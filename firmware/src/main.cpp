#include <Arduino.h>
#include <Wire.h>
#include <WiFi.h>
#include <WebServer.h>
#include <ESPmDNS.h>
#include <Preferences.h>
#include <ArduinoJson.h>
#include <U8g2lib.h>
#include <esp_partition.h>
#include <esp_system.h>
#include <esp_timer.h>
#include <sys/time.h>
#include <time.h>
#include "Journal.h"

using co2::Record;
constexpr uint8_t SDA_PIN=5,SCL_PIN=6,SENSOR_ADDR=0x62;
U8G2_SSD1306_72X40_ER_F_HW_I2C display(U8G2_R0,U8X8_PIN_NONE,SCL_PIN,SDA_PIN);
WebServer server(80);Preferences settings;
String deviceID,host,ssid,password,apiToken,line,lastError;
uint32_t bootID=0;uint64_t lastReading=0,lastPoll=0,lastOLED=0,lastMinute=0,lastReconnect=0,lastRetry=0,lastOLEDProbe=0;
bool sensorStarted=false,oledFound=false,mdnsStarted=false,httpStarted=false,ntpStarted=false;unsigned errors=0;
uint16_t latestCO2=0;float latestT=0,latestRH=0;double sumCO2=0,sumT=0,sumRH=0;unsigned samples=0;
class Flash:public co2::Storage{
 public:const esp_partition_t* part=nullptr;
 size_t size()const override{return part?part->size:0;}
 bool read(size_t p,void* d,size_t n)override{return part&&esp_partition_read(part,p,d,n)==ESP_OK;}
 bool write(size_t p,const void* d,size_t n)override{return part&&esp_partition_write(part,p,d,n)==ESP_OK;}
 bool erase(size_t p,size_t n)override{return part&&esp_partition_erase_range(part,p,n)==ESP_OK;}
} flash;
co2::Journal journal(flash);
uint64_t uptime(){return uint64_t(esp_timer_get_time())/1000000;}
uint32_t unixNow(){time_t t=time(nullptr);return t>=1735689600?uint32_t(t):0;}
bool probe(uint8_t a){Wire.beginTransmission(a);return Wire.endTransmission()==0;}
bool command(uint16_t c){Wire.beginTransmission(SENSOR_ADDR);Wire.write(uint8_t(c>>8));Wire.write(uint8_t(c));return Wire.endTransmission()==0;}
bool response(uint16_t c,uint16_t* out,size_t words){if(!command(c))return false;delay(2);size_t n=words*3;
 if(Wire.requestFrom(SENSOR_ADDR,uint8_t(n))!=n){while(Wire.available())Wire.read();return false;}
 for(size_t i=0;i<words;++i){uint8_t b[2]={uint8_t(Wire.read()),uint8_t(Wire.read())};uint8_t crc=Wire.read();if(co2::sensorCRC(b,2)!=crc){while(Wire.available())Wire.read();return false;}out[i]=(uint16_t(b[0])<<8)|b[1];}return true;}
void startSensor(){lastRetry=uptime();sensorStarted=false;
 if(!probe(SENSOR_ADDR)){lastError="sensor_not_found";return;}
 // Stop a measurement left running by a previous MCU reset; never factory-reset/calibrate.
 if(!command(0x3f86)){lastError="sensor_stop_failed";return;}delay(500);
 sensorStarted=command(0x21b1);lastError=sensorStarted?"warming_up":"sensor_start_failed";errors=0;
}
void recordJSON(JsonObject o,const Record&r){o["seq"]=r.seq;o["unix_s"]=r.unix_s;o["boot"]=r.boot;o["uptime_s"]=r.uptime_s;o["co2"]=r.co2;o["temperature"]=r.temp_centi/100.0;o["humidity"]=r.rh_centi/100.0;}
void statusJSON(JsonDocument&d){d["type"]="status";d["firmware"]="0.1.1";d["device_id"]=deviceID;d["host"]=host+".local";d["boot"]=bootID;d["uptime_s"]=uptime();d["unix_s"]=unixNow();
 d["sensor_started"]=sensorStarted;d["oled_found"]=oledFound;d["sda"]=SDA_PIN;d["scl"]=SCL_PIN;d["error"]=lastError;
 d["wifi_connected"]=WiFi.status()==WL_CONNECTED;d["ip"]=WiFi.status()==WL_CONNECTED?WiFi.localIP().toString():String("");d["paired"]=apiToken.length()>=32;
 if(lastReading){d["co2"]=latestCO2;d["temperature"]=latestT;d["humidity"]=latestRH;d["age_s"]=uptime()-lastReading;}else{d["co2"]=nullptr;d["age_s"]=nullptr;}
 JsonObject log=d.createNestedObject("journal");log["healthy"]=journal.healthy();log["capacity"]=journal.capacity();log["count"]=journal.count();log["oldest_seq"]=journal.first();log["newest_seq"]=journal.newest();log["interval_s"]=60;
}
void historyJSON(JsonDocument&d,uint64_t after,size_t limit){d["type"]="history";d["device_id"]=deviceID;d["oldest_seq"]=journal.first();d["newest_seq"]=journal.newest();d["requested_after"]=after;
 d["gap"]=journal.first()>1 && after<journal.first()-1;JsonArray a=d.createNestedArray("records");uint64_t next=after;
 bool ok=journal.after(after,limit,[&](const Record&r){recordJSON(a.createNestedObject(),r);next=r.seq;return true;});d["next_after"]=next;d["more"]=next<journal.newest();d["read_ok"]=ok;
}
void printJSON(JsonDocument&d){if(Serial){serializeJson(d,Serial);Serial.println();}}
void startWiFi(){if(ssid.isEmpty())return;WiFi.mode(WIFI_STA);WiFi.setHostname(host.c_str());WiFi.setAutoReconnect(true);WiFi.begin(ssid.c_str(),password.c_str());lastReconnect=uptime();}
bool authorized(){if(apiToken.length()<32||server.header("Authorization")!=String("Bearer ")+apiToken){server.send(401,"application/json","{\"error\":\"unauthorized\"}");return false;}return true;}
void setupHTTP(){const char* headers[]={"Authorization"};server.collectHeaders(headers,1);
 server.on("/api/status",HTTP_GET,[]{if(!authorized())return;DynamicJsonDocument d(2048);statusJSON(d);String s;serializeJson(d,s);server.send(200,"application/json",s);});
 server.on("/api/history",HTTP_GET,[]{if(!authorized())return;uint64_t after=strtoull(server.arg("after").c_str(),nullptr,10);size_t limit=server.hasArg("limit")?server.arg("limit").toInt():64;limit=constrain(limit,size_t(1),size_t(64));DynamicJsonDocument d(16384);historyJSON(d,after,limit);if(d.overflowed()){server.send(500,"application/json","{\"error\":\"response_too_large\"}");return;}String s;serializeJson(d,s);server.send(200,"application/json",s);});
 server.onNotFound([]{server.send(404,"application/json","{\"error\":\"not_found\"}");});
}
void serialCommand(const String&input){DynamicJsonDocument req(1024),reply(2048);reply["type"]="ack";auto err=deserializeJson(req,input);if(err){reply["error"]="invalid_json";printJSON(reply);return;}String cmd=req["cmd"]|"";
 if(cmd=="status"){statusJSON(reply);printJSON(reply);}
 else if(cmd=="scan"){reply["type"]="scan";JsonArray a=reply.createNestedArray("addresses");for(uint8_t i=1;i<127;++i)if(probe(i))a.add(i);printJSON(reply);}
 else if(cmd=="set_time"){uint32_t t=req["unix_s"]|0U;if(t>=1735689600){timeval tv{time_t(t),0};settimeofday(&tv,nullptr);reply["ok"]=true;}else reply["error"]="invalid_time";printJSON(reply);}
 else if(cmd=="configure"){
  String s=req["ssid"]|"",p=req["password"]|"",token=req["token"]|"";
  if(s.isEmpty()||s.length()>32||p.length()>64||token.length()<32||token.length()>64){reply["error"]="invalid_configuration";printJSON(reply);return;}
  settings.putString("ssid",s);settings.putString("password",p);settings.putString("token",token);ssid=s;password=p;apiToken=token;
  WiFi.disconnect();startWiFi();reply["type"]="configured";reply["ok"]=true;reply["device_id"]=deviceID;reply["host"]=host+".local";printJSON(reply);
 }
 else if(cmd=="history"){uint64_t after=req["after"]|uint64_t(0);size_t limit=constrain(size_t(req["limit"]|32U),size_t(1),size_t(64));DynamicJsonDocument h(16384);historyJSON(h,after,limit);printJSON(h);}
 else {reply["error"]="unknown_command";printJSON(reply);}
}
void pollSensor(){uint64_t now=uptime();if(now-lastPoll<1)return;lastPoll=now;
 if(!sensorStarted){if(now-lastRetry>=30)startSensor();return;}
 uint16_t ready=0;if(!response(0xe4b8,&ready,1)){lastError="i2c_or_crc_error";++errors;}
 else if((ready&0x7ff)!=0){uint16_t words[3];if(response(0xec05,words,3)&&words[0]>0&&words[0]<=40000){latestCO2=words[0];latestT=-45.0+175.0*words[1]/65535.0;latestRH=100.0*words[2]/65535.0;lastReading=now;lastError="";errors=0;sumCO2+=latestCO2;sumT+=latestT;sumRH+=latestRH;++samples;DynamicJsonDocument d(256);d["type"]="measurement";d["co2"]=latestCO2;d["temperature"]=latestT;d["humidity"]=latestRH;d["uptime_s"]=now;printJSON(d);}else{lastError="measurement_or_crc_error";++errors;}}
 if(errors>=5&&now-lastRetry>=30)startSensor();
}
void initOLED(){if(!probe(0x3c))return;
 // U8g2 configures GPIO modes before Wire.begin(). End the existing bus first,
 // otherwise Arduino sees it as running and does not restore the I2C pin matrix.
 Wire.end();display.setBusClock(100000);display.begin();Wire.setClock(100000);Wire.setTimeOut(50);oledFound=probe(0x3c);
}
void updateOLED(){if(!oledFound){if(uptime()-lastOLEDProbe>=5){lastOLEDProbe=uptime();initOLED();}if(!oledFound)return;}uint64_t now=uptime();if(now==lastOLED)return;lastOLED=now;display.clearBuffer();display.setFont(u8g2_font_5x7_tf);display.drawStr(0,7,"CO2 ppm");display.drawStr(66,7,WiFi.status()==WL_CONNECTED?"W":"-");
 if(lastReading&&now-lastReading<=20){char n[10];snprintf(n,sizeof(n),"%u",latestCO2);display.setFont(u8g2_font_logisoso18_tn);display.drawStr(0,28,n);char bottom[24];snprintf(bottom,sizeof(bottom),"%.1fC %.0f%%",latestT,latestRH);display.setFont(u8g2_font_5x7_tf);display.drawStr(0,39,bottom);}
 else {display.setFont(u8g2_font_5x7_tf);display.drawStr(0,23,sensorStarted?"WAIT / STALE":"NO SENSOR");display.drawStr(0,37,journal.healthy()?"USB: status":"LOG ERROR");}display.sendBuffer();
}
void setup(){Serial.begin(115200);delay(300);bootID=esp_random();uint64_t mac=ESP.getEfuseMac();char id[20];snprintf(id,sizeof(id),"%04x%08x",uint16_t(mac>>32),uint32_t(mac));deviceID=id;host="co2-"+deviceID.substring(6);
 Wire.begin(SDA_PIN,SCL_PIN,100000);Wire.setTimeOut(50);initOLED();
 flash.part=esp_partition_find_first(ESP_PARTITION_TYPE_DATA,esp_partition_subtype_t(0x40),"journal");journal.begin();
 settings.begin("co2-config",false);ssid=settings.getString("ssid","");password=settings.getString("password","");apiToken=settings.getString("token","");
 startSensor();startWiFi();setupHTTP();lastMinute=uptime();DynamicJsonDocument d(2048);statusJSON(d);d["reset_reason"]=int(esp_reset_reason());printJSON(d);
}
void loop(){uint64_t now=uptime();while(Serial.available()){char c=char(Serial.read());if(c=='\n'){if(!line.isEmpty())serialCommand(line);line="";}else if(c!='\r'){if(line.length()<768)line+=c;else line="";}}
 pollSensor();updateOLED();if(httpStarted)server.handleClient();
 if(WiFi.status()==WL_CONNECTED&&!httpStarted){server.begin();httpStarted=true;}
 if(WiFi.status()==WL_CONNECTED&&!ntpStarted){configTime(0,0,"pool.ntp.org","time.cloudflare.com");ntpStarted=true;}
 if(WiFi.status()==WL_CONNECTED&&!mdnsStarted){mdnsStarted=MDNS.begin(host.c_str());if(mdnsStarted)MDNS.addService("http","tcp",80);}
 if(!ssid.isEmpty()&&WiFi.status()!=WL_CONNECTED&&now-lastReconnect>=30){WiFi.reconnect();lastReconnect=now;}
 if(now-lastMinute>=60){lastMinute=now;if(samples){Record r{};r.unix_s=unixNow();r.boot=bootID;r.uptime_s=now;r.co2=uint16_t(lround(sumCO2/samples));r.temp_centi=int16_t(lround(sumT/samples*100));r.rh_centi=uint16_t(lround(sumRH/samples*100));if(!journal.append(r))lastError="flash_journal_error";sumCO2=sumT=sumRH=0;samples=0;}}
 delay(2);
}

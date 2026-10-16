import AppKit
import Foundation
import SQLite3
import Darwin

struct Sample: Decodable { let seq:Int64; let unix_s:Int64; let boot:Int64; let uptime_s:Int64; let co2:Double; let temperature:Double; let humidity:Double }
struct JournalInfo:Decodable { let healthy:Bool; let capacity:Int; let count:Int; let oldest_seq:Int64; let newest_seq:Int64 }
struct BoardStatus:Decodable { let device_id:String; let boot:Int64; let uptime_s:Double; let unix_s:Double; let co2:Double?; let temperature:Double?; let humidity:Double?; let age_s:Double?; let error:String; let journal:JournalInfo }
struct History:Decodable { let device_id:String;let oldest_seq:Int64;let newest_seq:Int64;let requested_after:Int64;let records:[Sample];let next_after:Int64;let more:Bool;let read_ok:Bool;let gap:Bool }
struct Configuration:Codable {var host:String="";var token:String=""}
struct Failure:LocalizedError {let message:String;var errorDescription:String?{message}}
let transient=unsafeBitCast(-1,to:sqlite3_destructor_type.self)

final class Store {
 var db:OpaquePointer?;let url:URL
 init(url:URL)throws{self.url=url;try FileManager.default.createDirectory(at:url.deletingLastPathComponent(),withIntermediateDirectories:true);guard sqlite3_open(url.path,&db)==SQLITE_OK else{throw Failure(message:"Не удалось открыть историю")}
  try exec("PRAGMA journal_mode=WAL; CREATE TABLE IF NOT EXISTS samples(device TEXT,seq INTEGER,unix_s INTEGER,boot INTEGER,uptime INTEGER,co2 REAL,t REAL,rh REAL,effective REAL,PRIMARY KEY(device,seq)); CREATE TABLE IF NOT EXISTS anchors(device TEXT,boot INTEGER,base REAL,PRIMARY KEY(device,boot)); CREATE TABLE IF NOT EXISTS gaps(device TEXT,first INTEGER,last INTEGER,PRIMARY KEY(device,first,last));")
 }
 deinit{sqlite3_close(db)}
 func exec(_ sql:String)throws{guard sqlite3_exec(db,sql,nil,nil,nil)==SQLITE_OK else{throw Failure(message:String(cString:sqlite3_errmsg(db)))}}
 func prepared(_ sql:String,_ values:[Any],_ body:(OpaquePointer)throws->Void)throws{var st:OpaquePointer?;guard sqlite3_prepare_v2(db,sql,-1,&st,nil)==SQLITE_OK,let q=st else{throw Failure(message:String(cString:sqlite3_errmsg(db)))};defer{sqlite3_finalize(q)}
  for (i,v) in values.enumerated(){let n=Int32(i+1);if let s=v as? String{sqlite3_bind_text(q,n,s,-1,transient)}else if let x=v as? Int64{sqlite3_bind_int64(q,n,x)}else if let x=v as? Double{sqlite3_bind_double(q,n,x)}else{sqlite3_bind_null(q,n)}};try body(q)
 }
 func scalar(_ sql:String,_ v:[Any]=[])throws->Int64{var result:Int64=0;try prepared(sql,v){q in if sqlite3_step(q)==SQLITE_ROW{result=sqlite3_column_int64(q,0)}};return result}
 func cursor(_ device:String)throws->Int64{try scalar("SELECT COALESCE(MAX(seq),0) FROM samples WHERE device=?",[device])}
 func anchor(device:String,boot:Int64,base:Double)throws {
  var prior:Double?;try prepared("SELECT base FROM anchors WHERE device=? AND boot=?",[device,boot]){q in if sqlite3_step(q)==SQLITE_ROW{prior=sqlite3_column_double(q,0)}}
  if let old=prior,abs(old-base)<2{return}
  try prepared("INSERT OR REPLACE INTO anchors VALUES(?,?,?)",[device,boot,base]){q in guard sqlite3_step(q)==SQLITE_DONE else{throw Failure(message:"Ошибка времени")}}
  try prepared("UPDATE samples SET effective=?+uptime WHERE device=? AND boot=? AND unix_s=0",[base,device,boot]){q in _=sqlite3_step(q)}
 }
 func ingest(_ history:History)throws {
  guard history.read_ok else{throw Failure(message:"Ошибка чтения памяти устройства")};try exec("BEGIN IMMEDIATE")
  do {for r in history.records{try prepared("INSERT OR IGNORE INTO samples VALUES(?,?,?,?,?,?,?,?,COALESCE(NULLIF(?,0),(SELECT base+? FROM anchors WHERE device=? AND boot=?)))",[history.device_id,r.seq,r.unix_s,r.boot,r.uptime_s,r.co2,r.temperature,r.humidity,r.unix_s,r.uptime_s,history.device_id,r.boot]){q in guard sqlite3_step(q)==SQLITE_DONE else{throw Failure(message:"Ошибка сохранения истории")}}}
   if history.gap {try prepared("INSERT OR IGNORE INTO gaps VALUES(?,?,?)",[history.device_id,history.requested_after+1,history.oldest_seq-1]){q in _=sqlite3_step(q)}}
   try exec("COMMIT")
  }catch{try? exec("ROLLBACK");throw error}
 }
 func points(hours:Double,device:String)throws->[(Double,Double)]{var a:[(Double,Double)]=[];try prepared("SELECT effective,co2 FROM samples WHERE device=? AND effective>=? ORDER BY effective",[device,Date().timeIntervalSince1970-hours*3600]){q in while sqlite3_step(q)==SQLITE_ROW{a.append((sqlite3_column_double(q,0),sqlite3_column_double(q,1)))}};return a}
 func export(to:URL)throws{var out="device_id,sequence,utc_time,device_unix_s,boot,uptime_s,co2_ppm,temperature_c,humidity_percent\n";let df=ISO8601DateFormatter()
  try prepared("SELECT device,seq,effective,unix_s,boot,uptime,co2,t,rh FROM samples ORDER BY device,seq",[]){q in while sqlite3_step(q)==SQLITE_ROW{let device=String(cString:sqlite3_column_text(q,0));let stamp=sqlite3_column_type(q,2)==SQLITE_NULL ? "" : df.string(from:Date(timeIntervalSince1970:sqlite3_column_double(q,2)));out += "\(device),\(sqlite3_column_int64(q,1)),\(stamp),\(sqlite3_column_int64(q,3)),\(sqlite3_column_int64(q,4)),\(sqlite3_column_int64(q,5)),\(sqlite3_column_double(q,6)),\(sqlite3_column_double(q,7)),\(sqlite3_column_double(q,8))\n"}}
  try out.write(to:to,atomically:true,encoding:.utf8)
 }
}

final class Transport {
 var config:Configuration;var mode="USB";static let usbQueue=DispatchQueue(label:"co2.usb")
 init(_ c:Configuration){config=c}
 static func port()throws->String{let ports=try FileManager.default.contentsOfDirectory(atPath:"/dev").filter{$0.hasPrefix("cu.usbmodem")};guard ports.count==1 else{throw Failure(message:ports.isEmpty ? "Подключите контроллер по USB или настройте Wi-Fi" : "Подключено несколько USB-плат")};return "/dev/"+ports[0]}
 static func usb(_ cmd:[String:Any],kind:String)throws->Data{
  let fd=Darwin.open(try port(),O_RDWR|O_NOCTTY|O_NONBLOCK);guard fd>=0 else{throw Failure(message:"Нет доступа к USB")};defer{Darwin.close(fd)}
  var cfg=termios();guard tcgetattr(fd,&cfg)==0 else{throw Failure(message:"Ошибка USB-порта")};cfmakeraw(&cfg);cfsetspeed(&cfg,speed_t(B115200));cfg.c_cflag |= tcflag_t(CLOCAL|CREAD);cfg.c_cflag &= ~tcflag_t(HUPCL);tcsetattr(fd,TCSANOW,&cfg);var rts=Int32(TIOCM_RTS);var dtr=Int32(TIOCM_DTR);_ = ioctl(fd,TIOCMBIC,&rts);_ = ioctl(fd,TIOCMBIS,&dtr);tcflush(fd,TCIFLUSH)
  var data=try JSONSerialization.data(withJSONObject:cmd);data.append(10);let wrote=data.withUnsafeBytes{Darwin.write(fd,$0.baseAddress,data.count)};guard wrote==data.count else{throw Failure(message:"Не удалось отправить запрос USB")}
  let deadline=Date().addingTimeInterval(8);var retry=Date().addingTimeInterval(1.5);var buffer=Data();var bytes=[UInt8](repeating:0,count:4096)
  while Date()<deadline{if Date()>=retry{_ = data.withUnsafeBytes{Darwin.write(fd,$0.baseAddress,data.count)};retry=Date().addingTimeInterval(1.5)};let n=Darwin.read(fd,&bytes,bytes.count);if n>0{buffer.append(contentsOf:bytes.prefix(n));if buffer.count>131072{throw Failure(message:"Слишком длинный ответ USB")}
    while let end=buffer.firstIndex(of:10){let line=buffer[..<end];buffer.removeSubrange(...end);if let object=try? JSONSerialization.jsonObject(with:Data(line)) as? [String:Any]{if object["type"] as? String == "ack",let error=object["error"] as? String{throw Failure(message:error)};if object["type"] as? String == kind{if kind=="history",let expected=cmd["after"] as? Int64,(object["requested_after"] as? NSNumber)?.int64Value != expected{continue};return Data(line)}}}
   }else if n<0 && errno != EAGAIN && errno != EINTR{throw Failure(message:"USB отключён")};Thread.sleep(forTimeInterval:0.02)}
  throw Failure(message:"Устройство не ответило по USB")
 }
 func data(command:[String:Any],kind:String,path:String)async throws->Data{
  if !config.host.isEmpty {
   do{let host=config.host.replacingOccurrences(of:"http://",with:"").trimmingCharacters(in:CharacterSet(charactersIn:"/ "));guard let url=URL(string:"http://\(host)\(path)") else{throw Failure(message:"Неверный адрес")};var req=URLRequest(url:url);req.timeoutInterval=4;req.setValue("Bearer "+config.token,forHTTPHeaderField:"Authorization");let(d,r)=try await URLSession.shared.data(for:req);guard (r as? HTTPURLResponse)?.statusCode==200 else{throw Failure(message:"Нет доступа по Wi-Fi: проверьте ключ")};mode="Wi-Fi";return d
   }catch{if (try? Self.port())==nil{throw error}}
  }
  mode="USB";return try await withCheckedThrowingContinuation{cont in Self.usbQueue.async{cont.resume(with:Result{try Self.usb(command,kind:kind)})}}
 }
 func status()async throws->BoardStatus{let d=try await data(command:["cmd":"status"],kind:"status",path:"/api/status");let status=try JSONDecoder().decode(BoardStatus.self,from:d);if mode=="USB" && status.unix_s==0{_ = try await data(command:["cmd":"set_time","unix_s":Int(Date().timeIntervalSince1970)],kind:"ack",path:"")};return status}
 func history(after:Int64)async throws->History{let d=try await data(command:["cmd":"history","after":after,"limit":64],kind:"history",path:"/api/history?after=\(after)&limit=64");return try JSONDecoder().decode(History.self,from:d)}
}

final class Plot:NSView {
 var values:[(Double,Double)]=[];var hours:Double=24
 override func draw(_ dirtyRect:NSRect){NSColor.windowBackgroundColor.setFill();bounds.fill();let area=bounds.insetBy(dx:65,dy:45)
  let label:[NSAttributedString.Key:Any]=[.font:NSFont.systemFont(ofSize:12),.foregroundColor:NSColor.secondaryLabelColor]
  guard values.count>1 else{("История появится после нескольких минут работы" as NSString).draw(at:NSPoint(x:65,y:bounds.midY),withAttributes:label);return}
  let now=Date().timeIntervalSince1970,start=now-hours*3600;let low=max(0,floor((values.map{$0.1}.min() ?? 400)/100)*100-100),high=max(low+200,ceil((values.map{$0.1}.max() ?? 1200)/100)*100+100)
  for i in 0...4{let y=area.minY+area.height*Double(i)/4;NSColor.separatorColor.setStroke();let p=NSBezierPath();p.move(to:NSPoint(x:area.minX,y:y));p.line(to:NSPoint(x:area.maxX,y:y));p.stroke();("\(Int(low+(high-low)*Double(i)/4))" as NSString).draw(at:NSPoint(x:12,y:y-7),withAttributes:label)}
  let path=NSBezierPath();var prior:Double?;for (t,v) in values{let pt=NSPoint(x:area.minX+(t-start)/(now-start)*area.width,y:area.minY+(v-low)/(high-low)*area.height);if let last=prior,t-last<180{path.line(to:pt)}else{path.move(to:pt)};prior=t};NSColor.controlAccentColor.setStroke();path.lineWidth=2;path.stroke()
  let df=DateFormatter();df.dateFormat=hours>24 ? "dd.MM HH:mm" : "HH:mm";for i in 0...4{let x=area.minX+area.width*Double(i)/4;let text=df.string(from:Date(timeIntervalSince1970:start+(now-start)*Double(i)/4));(text as NSString).draw(at:NSPoint(x:x-25,y:15),withAttributes:label)}
 }
}

final class App:NSObject,NSApplicationDelegate {
 var item:NSStatusItem!;var store:Store!;var transport:Transport!;var timer:Timer?;var busy=false;var current:BoardStatus?;var chartWindow:NSWindow?;var plot:Plot?
 var root:URL{FileManager.default.urls(for:.applicationSupportDirectory,in:.userDomainMask)[0].appendingPathComponent("CO2Monitor")}
 var configURL:URL{root.appendingPathComponent("config.json")}
 func applicationDidFinishLaunching(_ notification:Notification){do{store=try Store(url:root.appendingPathComponent("history.sqlite"))}catch{show(error.localizedDescription);NSApp.terminate(nil);return}
  let config=(try? JSONDecoder().decode(Configuration.self,from:Data(contentsOf:configURL))) ?? Configuration();transport=Transport(config);item=NSStatusBar.system.statusItem(withLength:NSStatusItem.variableLength);item.button?.title="CO₂ —";menu(message:"Подключение…");refresh();timer=Timer.scheduledTimer(withTimeInterval:5,repeats:true){[weak self]_ in self?.refresh()}
 }
 func menu(message:String){let m=NSMenu();let status=NSMenuItem(title:message,action:nil,keyEquivalent:"");m.addItem(status)
  if let s=current{if let t=s.temperature,let rh=s.humidity{m.addItem(withTitle:String(format:"%.1f °C · %.0f %% влажности",t,rh),action:nil,keyEquivalent:"")};m.addItem(withTitle:"На устройстве: \(s.journal.count) / \(s.journal.capacity) записей",action:nil,keyEquivalent:"");if !s.journal.healthy{m.addItem(withTitle:"Ошибка журнала на устройстве",action:nil,keyEquivalent:"")}}
  m.addItem(.separator());for (title,action) in [("График за 24 часа",#selector(graph24)),("График за 7 дней",#selector(graph7)),("Экспортировать CSV…",#selector(exportCSV)),("Настроить Wi-Fi по USB…",#selector(wifi)),("Адрес и ключ доступа…",#selector(settings)),("Открыть папку истории",#selector(folder))]{let i=NSMenuItem(title:title,action:action,keyEquivalent:"");i.target=self;m.addItem(i)};m.addItem(.separator());let q=NSMenuItem(title:"Завершить",action:#selector(quit),keyEquivalent:"q");q.target=self;m.addItem(q);item.menu=m
 }
 func refresh(){guard !busy else{return};busy=true
  Task{@MainActor in defer{busy=false};do{let s=try await transport.status();current=s;let base=(s.unix_s>0 ? s.unix_s : Date().timeIntervalSince1970)-s.uptime_s;try store.anchor(device:s.device_id,boot:s.boot,base:base)
    var cursor=try store.cursor(s.device_id);if cursor>s.journal.newest_seq{throw Failure(message:"Журнал устройства сброшен; архив Mac сохранён")};var missed=false
    for _ in 0..<8 {let h=try await transport.history(after:cursor);guard h.device_id==s.device_id else{throw Failure(message:"Ответило другое устройство")};missed = missed || h.gap;try store.ingest(h);if !h.more{break};guard h.next_after>cursor else{throw Failure(message:"Ошибка последовательности журнала")};cursor=h.next_after}
    if let c=s.co2,let age=s.age_s,age<=20{item.button?.title="CO₂ \(Int(c.rounded())) ppm";menu(message:"\(transport.mode) · обновлено \(Int(age)) с назад"+((missed || ((try? store.scalar("SELECT COUNT(*) FROM gaps WHERE device=?",[s.device_id])) ?? 0)>0) ? " · есть пропуск истории":""))}else{item.button?.title="CO₂ —";menu(message:s.error.isEmpty ? "Ожидание измерения" : "Датчик: \(s.error)")};if let p=plot{p.values=(try? store.points(hours:p.hours,device:s.device_id)) ?? [];p.needsDisplay=true}
   }catch{item.button?.title="CO₂ —";menu(message:error.localizedDescription)}}
 }
 func show(_ text:String){let a=NSAlert();a.messageText="CO2 Monitor";a.informativeText=text;a.runModal()}
 @objc func graph24(){graph(hours:24)};@objc func graph7(){graph(hours:168)}
 func graph(hours:Double){guard let s=current else{show("Сначала подключите устройство");return};let window=NSWindow(contentRect:NSRect(x:0,y:0,width:800,height:430),styleMask:[.titled,.closable,.resizable],backing:.buffered,defer:false);window.title=hours==24 ? "CO₂ · последние 24 часа" : "CO₂ · последние 7 дней";let view=Plot(frame:window.contentView!.bounds);view.autoresizingMask=[.width,.height];view.hours=hours;view.values=(try? store.points(hours:hours,device:s.device_id)) ?? [];window.contentView=view;window.center();window.isReleasedWhenClosed=false;window.makeKeyAndOrderFront(nil);NSApp.activate(ignoringOtherApps:true);chartWindow=window;plot=view}
 @objc func exportCSV(){let panel=NSSavePanel();panel.nameFieldStringValue="co2-history.csv";NSApp.activate(ignoringOtherApps:true);if panel.runModal() == .OK,let url=panel.url{do{try store.export(to:url)}catch{show(error.localizedDescription)}}}
 @objc func folder(){NSWorkspace.shared.open(root)}
 @objc func settings(){let a=NSAlert();a.messageText="Подключение по Wi-Fi";a.informativeText="Пустой адрес — подключение по USB. Для работы от power bank сначала настройте сеть через USB.";a.addButton(withTitle:"Сохранить");a.addButton(withTitle:"Отмена");let v=NSView(frame:NSRect(x:0,y:0,width:380,height:90));let host=NSTextField(frame:NSRect(x:0,y:55,width:380,height:25));host.placeholderString="co2-xxxxxx.local или IP";host.stringValue=transport.config.host;let key=NSSecureTextField(frame:NSRect(x:0,y:15,width:380,height:25));key.placeholderString="Ключ доступа";key.stringValue=transport.config.token;v.addSubview(host);v.addSubview(key);a.accessoryView=v;NSApp.activate(ignoringOtherApps:true);if a.runModal() == .alertFirstButtonReturn{let c=Configuration(host:host.stringValue.trimmingCharacters(in:.whitespacesAndNewlines),token:key.stringValue);do{try JSONEncoder().encode(c).write(to:configURL,options:.atomic);try FileManager.default.setAttributes([.posixPermissions:0o600],ofItemAtPath:configURL.path);transport.config=c;refresh()}catch{show(error.localizedDescription)}}}
 @objc func wifi(){guard let project=Bundle.main.object(forInfoDictionaryKey:"CO2ProjectPath") as? String else{show("Откройте настройку Wi-Fi в папке проекта");return};NSWorkspace.shared.open(URL(fileURLWithPath:project).appendingPathComponent("Настроить Wi-Fi.command"))}
 @objc func quit(){NSApp.terminate(nil)}
}
func selfTest()throws{
 let base=URL(fileURLWithPath:CommandLine.arguments.last!);let db=try Store(url:base.appendingPathComponent("test.sqlite"))
 func check(_ condition:Bool,_ text:String)throws{if !condition{throw Failure(message:"SELF TEST: "+text)}}
 let record=Sample(seq:1,unix_s:0,boot:3,uptime_s:60,co2:812,temperature:23.4,humidity:45)
 let h=History(device_id:"test-device",oldest_seq:1,newest_seq:1,requested_after:0,records:[record],next_after:1,more:false,read_ok:true,gap:false)
 try db.ingest(h);try db.ingest(h);let count=try db.scalar("SELECT COUNT(*) FROM samples");try check(count==1,"duplicate import");let cursor=try db.cursor("test-device");try check(cursor==1,"cursor")
 try db.anchor(device:"test-device",boot:3,base:1700000000);let time=try db.scalar("SELECT effective FROM samples");try check(time==1700000060,"time recovery")
 let gap=History(device_id:"other",oldest_seq:100,newest_seq:100,requested_after:0,records:[],next_after:0,more:false,read_ok:true,gap:true);try db.ingest(gap);let missing=try db.scalar("SELECT last-first+1 FROM gaps WHERE device='other'");try check(missing==99,"gap interval")
 try db.export(to:base.appendingPathComponent("test.csv"));let csv=try String(contentsOf:base.appendingPathComponent("test.csv"),encoding:.utf8);try check(csv.contains("812.0"),"CSV content")
 print("PASS: SQLite duplicate import, cursor, time recovery, gap accounting, CSV")
}
func usbCheck()throws{
 let root=URL(fileURLWithPath:CommandLine.arguments.last!);let store=try Store(url:root.appendingPathComponent("history.sqlite"))
 let raw=try Transport.usb(["cmd":"status"],kind:"status");let status=try JSONDecoder().decode(BoardStatus.self,from:raw)
 try store.anchor(device:status.device_id,boot:status.boot,base:(status.unix_s>0 ? status.unix_s : Date().timeIntervalSince1970)-status.uptime_s)
 var cursor=try store.cursor(status.device_id)
 for _ in 0..<10{let data=try Transport.usb(["cmd":"history","after":cursor,"limit":64],kind:"history");let h=try JSONDecoder().decode(History.self,from:data);try store.ingest(h);if !h.more{break};guard h.next_after>cursor else{throw Failure(message:"Cursor stalled")};cursor=h.next_after}
 print("PASS: native USB status/history; CO2=\(status.co2 ?? 0); saved=\(try store.cursor(status.device_id))")
}
if CommandLine.arguments.contains("--usb-check"){do{try usbCheck();exit(0)}catch{fputs("\(error)\n",stderr);exit(1)}}
if CommandLine.arguments.contains("--self-test"){do{try selfTest();exit(0)}catch{fputs("\(error)\n",stderr);exit(1)}}
let app=NSApplication.shared;let delegate=App();app.delegate=delegate;app.setActivationPolicy(.accessory);app.run()

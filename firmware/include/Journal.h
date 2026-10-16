#pragma once
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include <limits.h>
namespace co2 {
inline uint8_t sensorCRC(const uint8_t* p,size_t n){uint8_t c=0xff;while(n--){c^=*p++;for(int i=0;i<8;++i)c=(c&0x80)?uint8_t((c<<1)^0x31):uint8_t(c<<1);}return c;}
inline uint16_t crc16(const uint8_t* p,size_t n){uint16_t c=0xffff;while(n--){c^=uint16_t(*p++)<<8;for(int i=0;i<8;++i)c=(c&0x8000)?uint16_t((c<<1)^0x1021):uint16_t(c<<1);}return c;}
#pragma pack(push,1)
struct Record {uint32_t magic;uint64_t seq;uint32_t unix_s,boot,uptime_s;uint16_t co2;int16_t temp_centi;uint16_t rh_centi,crc;};
#pragma pack(pop)
static_assert(sizeof(Record)==32,"Persistent record format");
inline bool valid(const Record& r){return r.magic==0x434f3201 && r.seq>0 && r.crc==crc16(reinterpret_cast<const uint8_t*>(&r),30);}
struct Storage {virtual size_t size()const=0;virtual bool read(size_t,void*,size_t)=0;virtual bool write(size_t,const void*,size_t)=0;virtual bool erase(size_t,size_t)=0;virtual ~Storage(){};};
class Journal {
 Storage& s;size_t next=0;uint64_t last=0,oldest=0;size_t count_=0;bool healthy_=false;
 static constexpr size_t sector=4096,perSector=128;
 bool scan(){uint8_t buf[sector];uint64_t hi=0,lo=UINT64_MAX;size_t best=0,c=0;
  for(size_t off=0;off<s.size();off+=sector){if(!s.read(off,buf,sector))return false;for(size_t i=0;i<perSector;++i){Record r;memcpy(&r,buf+i*sizeof(r),sizeof(r));if(valid(r)){++c;if(r.seq>hi){hi=r.seq;best=off/sizeof(r)+i;}if(r.seq<lo)lo=r.seq;}}}
  last=hi;oldest=c?lo:0;count_=c;next=c?(best+1)%capacity():0;return true;}
 public:
 explicit Journal(Storage& store):s(store){}
 bool begin(){healthy_=s.size()>=sector*2 && s.size()%sector==0 && scan();return healthy_;}
 bool healthy()const{return healthy_;}size_t capacity()const{return s.size()/sizeof(Record);}size_t count()const{return count_;}uint64_t newest()const{return last;}uint64_t first()const{return oldest;}
 bool append(Record r){if(!healthy_)return false;
  // Never write over programmed or torn bytes. Preserve earlier records in that sector.
  for(int tries=0;tries<2;++tries){
   if(next%perSector==0){size_t target=next;uint64_t remembered=last;
    if(!s.erase(target*sizeof(Record),sector)){healthy_=false;return false;}
    if(!scan()){healthy_=false;return false;}next=target;if(last<remembered)last=remembered;
   }
   Record prior;if(!s.read(next*sizeof(Record),&prior,sizeof(prior))){healthy_=false;return false;}
   bool blank=true;for(uint8_t b:reinterpret_cast<const uint8_t(&)[32]>(prior))if(b!=0xff)blank=false;
   if(!blank){next=((next/perSector+1)*perSector)%capacity();continue;}
   r.magic=0x434f3201;r.seq=last+1;r.crc=crc16(reinterpret_cast<const uint8_t*>(&r),30);
   if(!s.write(next*sizeof(Record),&r,sizeof(r))){healthy_=false;return false;}
   Record verify;if(!s.read(next*sizeof(Record),&verify,sizeof(verify))||!valid(verify)||memcmp(&verify,&r,sizeof(r))){healthy_=false;return false;}
   last=r.seq;if(!count_)oldest=r.seq;++count_;next=(next+1)%capacity();return true;
  }healthy_=false;return false;
 }
 template<class F> bool after(uint64_t seq,size_t limit,F fn) {
  size_t delivered=0;uint8_t page[sector];size_t cached=SIZE_MAX;
  for(size_t i=0;i<capacity();++i){size_t slot=(next+i)%capacity(),block=slot/perSector;
   if(block!=cached){if(!s.read(block*sector,page,sector))return false;cached=block;}
   Record r;memcpy(&r,page+(slot%perSector)*sizeof(r),sizeof(r));
   if(valid(r)&&r.seq>seq){if(!fn(r))return false;if(++delivered>=limit)break;}}
  return true;
 }
};
}

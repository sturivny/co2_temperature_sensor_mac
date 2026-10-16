#include "Journal.h"
#include <vector>
#include <cassert>
#include <iostream>
#include <algorithm>
struct Memory:co2::Storage{
 std::vector<uint8_t> b;int cut=-1;Memory(size_t n=8192):b(n,255){}
 size_t size()const override{return b.size();}
 bool read(size_t p,void* d,size_t n)override{if(p+n>b.size())return false;memcpy(d,b.data()+p,n);return true;}
 bool write(size_t p,const void* v,size_t n)override{auto d=(const uint8_t*)v;size_t take=cut<0?n:std::min(n,size_t(cut));for(size_t i=0;i<take;++i){assert((b[p+i]&d[i])==d[i]);b[p+i]&=d[i];}return take==n;}
 bool erase(size_t p,size_t n)override{assert(p%4096==0&&n==4096);std::fill(b.begin()+p,b.begin()+p+n,255);return true;}
};
co2::Record record(){co2::Record r{};r.co2=812;r.temp_centi=2345;r.rh_centi=4500;r.boot=123;r.uptime_s=60;return r;}
int main(){uint8_t v[]={0xbe,0xef};assert(co2::sensorCRC(v,2)==0x92);assert(co2::crc16((const uint8_t*)"123456789",9)==0x29b1);
 Memory s;co2::Journal j(s);assert(j.begin());assert(j.count()==0);assert(j.append(record()));
 co2::Journal boot(s);assert(boot.begin());assert(boot.newest()==1&&boot.first()==1);
 // Simulate power loss after every partial byte count, preserving earlier valid samples.
 for(int cut=0;cut<32;++cut){Memory torn=s;torn.cut=cut;co2::Journal x(torn);assert(x.begin());assert(!x.append(record()));torn.cut=-1;co2::Journal y(torn);assert(y.begin());assert(y.newest()==1);assert(y.append(record()));std::vector<uint64_t> ids;y.after(0,100,[&](const co2::Record&r){ids.push_back(r.seq);return true;});assert((ids==std::vector<uint64_t>{1,2}));}
 // Multiple wraps, reboots, and paginated chronological replay without duplicates.
 Memory ring(4096*3);co2::Journal r(ring);assert(r.begin());for(int i=0;i<1800;++i)assert(r.append(record()));
 co2::Journal rb(ring);assert(rb.begin());assert(rb.newest()==1800);assert(rb.count()>=257&&rb.count()<=384);
 uint64_t cursor=0;size_t seen=0;while(true){size_t got=0;assert(rb.after(cursor,17,[&](const co2::Record&v){assert(v.seq>cursor);cursor=v.seq;++seen;++got;return true;}));if(!got)break;}
 assert(seen==rb.count());assert(cursor==1800);
 // Corruption must not turn a damaged record into plausible data.
 ring.b[0]^=1;co2::Journal damaged(ring);assert(damaged.begin());assert(damaged.newest()<=1800);
 std::cout<<"PASS: sensor CRC, journal CRC, 32 power-cut positions, circular rollover, reboot, pagination, corruption\n";
}

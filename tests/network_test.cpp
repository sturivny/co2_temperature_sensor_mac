#include "NetworkLifecycle.h"
#include <cassert>
#include <iostream>
int main(){
 co2::NetworkLifecycle net;
 auto a=net.update(false,0,0);assert(!a.stop&&!a.start);
 a=net.update(true,0,1);assert(!a.stop&&!a.start); // association without an IP
 a=net.update(true,12,2);assert(!a.stop&&a.start);
 a=net.update(true,12,2);assert(!a.stop&&!a.start);
 a=net.update(false,12,3);assert(a.stop&&!a.start);
 a=net.update(false,0,3);assert(!a.stop&&!a.start);
 a=net.update(true,12,4);assert(!a.stop&&a.start); // same DHCP lease after a drop
 a=net.update(true,13,4);assert(a.stop&&a.start); // address change
 a=net.update(true,13,6);assert(a.stop&&a.start); // drop/reconnect between polls
 for(unsigned i=7;i<107;++i){a=net.update(true,13,i);assert(a.stop&&a.start);}
 std::cout<<"PASS: network loss, same-IP reconnect, DHCP change, missed-between-polls reconnect, repeated recovery\n";
}

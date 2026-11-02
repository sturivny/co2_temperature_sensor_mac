#pragma once
#include <stdint.h>

namespace co2 {
struct NetworkAction { bool stop; bool start; };
// Event generation also catches a reconnect that completes between loop iterations.
class NetworkLifecycle {
 bool online_ = false;
 uint32_t ip_ = 0, generation_ = 0;
public:
 NetworkAction update(bool connected, uint32_t ip, uint32_t generation) {
  connected = connected && ip != 0;
  if (!connected) {
   bool stop = online_;
   online_ = false; ip_ = 0; generation_ = generation;
   return {stop, false};
  }
  bool changed = online_ && (ip != ip_ || generation != generation_);
  bool start = !online_ || changed;
  online_ = true; ip_ = ip; generation_ = generation;
  return {changed, start};
 }
};
}

/**
 * Parallel VLSI Wire Routing via MPI
 * Name 1(andrew_id 1), Name 2(andrew_id 2)
 */

#ifndef __WIREOPT_H__
#define __WIREOPT_H__

#include <cstdint>
#include <vector>

#define MAX_PTS_PER_WIRE 4
#define COST_REPORT_DEPTH 10

/** README(student):
 We provide two options for validating consistency between wire layout
 and occupancy:
 - After your program is finished and the output written to a file,
   you can run ./validate.py -r <route_file> -c <cost_file>.
 - If you wish to validate your data within the program, or between batches,
   you can create a wr_checker that tracks your data structures:
    wr_checker Checker(wires, occupancy);
   and call its validate() method from your code.
 The struct below is the standard format for wires used by the wire checker.
 It contains a buffer that holds up to four points, and a num_pts field 
 that specifies the number of points.
 Regardless of what representation you use for your wires, you should 
 implement the Wire::to_validate_format method to convert your Wire
 to a validate_wire_t if you wish to use the checker.
*/
struct validate_wire_t {
  uint8_t num_pts;
  struct {
    uint16_t x;
    uint16_t y;
  } p[MAX_PTS_PER_WIRE];
  validate_wire_t &cleanup(void);
  void print_wire(void) const;
};

struct Wire {
  /* Define the data structure for wire here. */ 
  int start_x, start_y, end_x, end_y, bend1_x, bend1_y;
  validate_wire_t to_validate_format(void) const;
};

struct wr_checker {
  std::vector<Wire> wires;
  std::vector<std::vector<int>> occupancies;
  const int nwires;
  const int dim_x;
  const int dim_y;
  wr_checker(std::vector<Wire> &wires, std::vector<std::vector<int>> &occupancies) 
  : wires(wires), occupancies(occupancies), nwires(wires.size()), dim_x(occupancies[0].size()), dim_y(occupancies.size()) {}
  void validate() const;
};

#endif

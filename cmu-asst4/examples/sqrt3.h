#ifndef _SQRT3_H
#define _SQRT3_H

#include <math.h>

// Check if x and y are approximately equal
static inline int approxEqual(float x, float y) { return (fabs(x - y) < 1e-6); }

static inline int min(int x, int y) { return (x < y) ? x : y; }

// Approximate sqrt(3) with different starting conditions
float approxSqrt3(float x);

// Perform computation
void compute(int procID, int nproc);

#endif // _SQRT3_H

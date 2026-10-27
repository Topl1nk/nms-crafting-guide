// The spring of the site's motion (made by scripts/make_spring.py; do not edit): a damped spring, overshooting a little.
export const SPRING_POINTS = [0.0, 0.0515, 0.1789, 0.3458, 0.5237, 0.692, 0.8372, 0.9526, 1.0363, 1.0902, 1.1185, 1.1263, 1.1195, 1.1032, 1.082, 1.0595, 1.0383, 1.0201, 1.0056, 0.9952, 0.9885, 0.985, 0.984, 0.985, 0.987, 0.9897, 0.9926, 0.9952, 0.9975, 0.9993, 1.0006, 1.0015, 1.0019, 1.002, 1.0019, 1.0];
export const SPRING = "linear(0, 0.0515, 0.1789, 0.3458, 0.5237, 0.692, 0.8372, 0.9526, 1.0363, 1.0902, 1.1185, 1.1263, 1.1195, 1.1032, 1.082, 1.0595, 1.0383, 1.0201, 1.0056, 0.9952, 0.9885, 0.985, 0.984, 0.985, 0.987, 0.9897, 0.9926, 0.9952, 0.9975, 0.9993, 1.0006, 1.0015, 1.0019, 1.002, 1.0019, 1)";
/** The spring at time t in 0..1 (the same curve as SPRING, for animations that are worked out in script). */
export function springAt(t) {
  if (t <= 0) return 0;
  if (t >= 1) return 1;
  const x = t * (SPRING_POINTS.length - 1);
  const i = Math.floor(x);
  return SPRING_POINTS[i] + (SPRING_POINTS[i + 1] - SPRING_POINTS[i]) * (x - i);
}

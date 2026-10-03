import { motion, useMotionValue, useReducedMotion, useSpring, useTransform } from "framer-motion";
import type { ReactNode } from "react";
import { cn } from "@/lib/format";

/** A card that tilts in 3D towards the pointer, with a soft moving highlight. */
export function TiltCard({ children, className }: { children: ReactNode; className?: string }) {
  const reduce = useReducedMotion();
  const x = useMotionValue(0.5);
  const y = useMotionValue(0.5);
  const rotateX = useSpring(useTransform(y, [0, 1], [8, -8]), { stiffness: 200, damping: 20 });
  const rotateY = useSpring(useTransform(x, [0, 1], [-10, 10]), { stiffness: 200, damping: 20 });
  const glow = useTransform(
    [x, y] as never,
    ([px, py]: number[]) =>
      `radial-gradient(240px circle at ${px! * 100}% ${py! * 100}%, rgb(99 102 241 / 0.14), transparent 70%)`,
  );

  return (
    <motion.div
      style={reduce ? undefined : { rotateX, rotateY, transformPerspective: 900 }}
      onPointerMove={(e) => {
        const r = e.currentTarget.getBoundingClientRect();
        x.set((e.clientX - r.left) / r.width);
        y.set((e.clientY - r.top) / r.height);
      }}
      onPointerLeave={() => {
        x.set(0.5);
        y.set(0.5);
      }}
      className={cn("relative overflow-hidden", className)}
    >
      {!reduce && (
        <motion.div
          aria-hidden
          className="pointer-events-none absolute inset-0"
          style={{ background: glow }}
        />
      )}
      <div className="relative">{children}</div>
    </motion.div>
  );
}

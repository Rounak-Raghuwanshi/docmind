/**
 * The workspace's embedding space in 3D. Every dot is one chunk; PCA squeezes its 384-number
 * vector into x/y/z. Chunks about similar topics land near each other, which is exactly what
 * vector search relies on. Drag to rotate, scroll to zoom, hover a dot to read it.
 */
import { Html, OrbitControls } from "@react-three/drei";
import { Canvas, type ThreeEvent } from "@react-three/fiber";
import { useLayoutEffect, useMemo, useRef, useState } from "react";
import * as THREE from "three";
import type { EmbeddingPoint } from "@/api/types";
import { useUi } from "@/stores/ui";

const SCALE = 3;

function cssColor(name: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim() || "#94a3b8";
}

function Points({
  points,
  colorOf,
  onHover,
}: {
  points: EmbeddingPoint[];
  colorOf: (p: EmbeddingPoint) => { color: string; dim: boolean };
  onHover: (i: number | null) => void;
}) {
  const ref = useRef<THREE.InstancedMesh>(null);
  useLayoutEffect(() => {
    const mesh = ref.current;
    if (!mesh) return;
    const m = new THREE.Matrix4();
    const c = new THREE.Color();
    points.forEach((p, i) => {
      const { color, dim } = colorOf(p);
      m.makeScale(dim ? 0.6 : 1, dim ? 0.6 : 1, dim ? 0.6 : 1);
      m.setPosition(p.x * SCALE, p.y * SCALE, p.z * SCALE);
      mesh.setMatrixAt(i, m);
      mesh.setColorAt(i, c.set(color));
    });
    mesh.instanceMatrix.needsUpdate = true;
    if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true;
  }, [points, colorOf]);

  return (
    <instancedMesh
      ref={ref}
      args={[undefined, undefined, points.length]}
      onPointerMove={(e: ThreeEvent<PointerEvent>) => {
        e.stopPropagation();
        onHover(e.instanceId ?? null);
      }}
      onPointerOut={() => onHover(null)}
    >
      <sphereGeometry args={[0.09, 16, 16]} />
      <meshBasicMaterial toneMapped={false} />
    </instancedMesh>
  );
}

function Axes() {
  const grid = cssColor("--chart-grid");
  const muted = cssColor("--chart-muted");
  return (
    <group>
      <gridHelper args={[SCALE * 2.2, 11, grid, grid]} position={[0, -SCALE * 1.05, 0]} />
      {(
        [
          ["PC1", [SCALE * 1.15, 0, 0]],
          ["PC2", [0, SCALE * 1.15, 0]],
          ["PC3", [0, 0, SCALE * 1.15]],
        ] as const
      ).map(([label, pos]) => (
        <Html
          key={label}
          position={pos as unknown as [number, number, number]}
          center
          style={{ color: muted, fontSize: 10, pointerEvents: "none" }}
        >
          {label}
        </Html>
      ))}
    </group>
  );
}

export function EmbeddingMap({
  points,
  colorOf,
}: {
  points: EmbeddingPoint[];
  colorOf: (p: EmbeddingPoint) => { color: string; dim: boolean };
}) {
  const [hover, setHover] = useState<number | null>(null);
  const theme = useUi((s) => s.theme);
  // Re-read CSS colour tokens when the theme flips.
  const key = useMemo(
    () => `${theme}-${document.documentElement.classList.contains("dark")}`,
    [theme],
  );
  const hovered = hover !== null ? points[hover] : undefined;
  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  return (
    <Canvas
      key={key}
      camera={{ position: [6, 4, 7], fov: 45 }}
      dpr={[1, 1.75]}
      style={{ cursor: hover !== null ? "pointer" : "grab" }}
    >
      <Axes />
      <Points points={points} colorOf={colorOf} onHover={setHover} />
      {hovered && (
        <Html
          position={[hovered.x * SCALE, hovered.y * SCALE, hovered.z * SCALE]}
          style={{ pointerEvents: "none" }}
          zIndexRange={[20, 0]}
        >
          <div className="ml-3 w-64 -translate-y-1/2 rounded-lg border border-slate-200 bg-white p-2.5 text-xs shadow-lg dark:border-slate-700 dark:bg-slate-900">
            <p className="font-semibold text-slate-900 dark:text-slate-100">
              {hovered.filename} · p. {hovered.page}
            </p>
            <p className="mt-1 line-clamp-4 text-slate-600 dark:text-slate-300">
              {hovered.preview}…
            </p>
          </div>
        </Html>
      )}
      <OrbitControls
        enablePan={false}
        autoRotate={hover === null && !reduced}
        autoRotateSpeed={0.6}
        minDistance={4}
        maxDistance={16}
      />
    </Canvas>
  );
}

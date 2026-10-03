/**
 * Landing-page 3D scene: an "AI core" with documents orbiting it inside a cloud of
 * embedding particles, joined by pulsing citation links. It follows the pointer gently and
 * stays still for people who prefer reduced motion.
 */
import { Float, Line, MeshDistortMaterial, RoundedBox } from "@react-three/drei";
import { Canvas, useFrame } from "@react-three/fiber";
import { useMemo, useRef } from "react";
import * as THREE from "three";
import type { Line2 } from "three-stdlib";

const BRAND = "#6366f1";
const BRAND_LIGHT = "#a5b4fc";
const ACCENT = "#22d3ee";

function prefersReducedMotion(): boolean {
  return (
    typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches
  );
}

function Core() {
  const shell = useRef<THREE.Mesh>(null);
  useFrame((_, dt) => {
    if (shell.current) {
      shell.current.rotation.y += dt * 0.15;
      shell.current.rotation.x += dt * 0.05;
    }
  });
  return (
    <group>
      <mesh>
        <icosahedronGeometry args={[1, 16]} />
        <MeshDistortMaterial
          color={BRAND}
          emissive={BRAND}
          emissiveIntensity={0.35}
          roughness={0.2}
          metalness={0.4}
          distort={0.35}
          speed={1.6}
        />
      </mesh>
      <mesh ref={shell} scale={1.45}>
        <icosahedronGeometry args={[1, 1]} />
        <meshBasicMaterial color={BRAND_LIGHT} wireframe transparent opacity={0.25} />
      </mesh>
    </group>
  );
}

/** A document page: a thin rounded slab with a few "text lines" on it. */
function DocCard({
  position,
  rotation,
  accent,
}: {
  position: [number, number, number];
  rotation: number;
  accent: string;
}) {
  return (
    <Float speed={1.4} rotationIntensity={0.5} floatIntensity={0.8}>
      <group position={position} rotation={[0, rotation, 0.08]}>
        <RoundedBox args={[0.9, 1.2, 0.04]} radius={0.06} smoothness={4}>
          <meshStandardMaterial color="#ffffff" roughness={0.35} metalness={0.05} />
        </RoundedBox>
        {[0.38, 0.24, 0.1, -0.04, -0.18].map((y, i) => (
          <mesh key={y} position={[-0.05 + (i === 0 ? -0.08 : 0), y, 0.026]}>
            <planeGeometry args={[i === 0 ? 0.5 : 0.66 - (i % 2) * 0.16, i === 0 ? 0.07 : 0.04]} />
            <meshBasicMaterial color={i === 0 ? accent : "#cbd5e1"} />
          </mesh>
        ))}
        <mesh position={[0.22, -0.38, 0.026]}>
          <circleGeometry args={[0.08, 24]} />
          <meshBasicMaterial color={accent} />
        </mesh>
      </group>
    </Float>
  );
}

function Orbit() {
  const group = useRef<THREE.Group>(null);
  const cards = useMemo(
    () =>
      Array.from({ length: 6 }, (_, i) => {
        const a = (i / 6) * Math.PI * 2;
        const r = 3;
        return {
          pos: [Math.cos(a) * r, Math.sin(a * 2) * 0.5, Math.sin(a) * r] as [
            number,
            number,
            number,
          ],
          rot: -a + Math.PI / 2,
          accent: i % 2 ? ACCENT : BRAND,
        };
      }),
    [],
  );
  useFrame((_, dt) => {
    if (group.current) group.current.rotation.y += dt * 0.12;
  });
  return (
    <group ref={group}>
      {cards.map((c, i) => (
        <group key={i}>
          <DocCard position={c.pos} rotation={c.rot} accent={c.accent} />
          <CitationLink to={c.pos} delay={i * 0.6} />
        </group>
      ))}
    </group>
  );
}

/** A curved beam from the core to a document that brightens and fades like a retrieval hit. */
function CitationLink({ to, delay }: { to: [number, number, number]; delay: number }) {
  const ref = useRef<Line2>(null);
  const points = useMemo(() => {
    const end = new THREE.Vector3(...to);
    const mid = end
      .clone()
      .multiplyScalar(0.5)
      .add(new THREE.Vector3(0, 0.9, 0));
    return new THREE.QuadraticBezierCurve3(new THREE.Vector3(0, 0, 0), mid, end).getPoints(32);
  }, [to]);
  useFrame(({ clock }) => {
    if (ref.current)
      ref.current.material.opacity =
        0.08 + Math.max(0, Math.sin(clock.elapsedTime * 1.2 - delay)) * 0.5;
  });
  return (
    <Line ref={ref} points={points} color={ACCENT} lineWidth={1.4} transparent opacity={0.2} />
  );
}

/** Embedding space: points on a fuzzy sphere, coloured by "topic". */
function Particles({ count = 900 }: { count?: number }) {
  const ref = useRef<THREE.Points>(null);
  const { positions, colors } = useMemo(() => {
    const positions = new Float32Array(count * 3);
    const colors = new Float32Array(count * 3);
    const palette = [new THREE.Color(BRAND), new THREE.Color(ACCENT), new THREE.Color(BRAND_LIGHT)];
    for (let i = 0; i < count; i++) {
      const r = 4.2 + Math.random() * 2.2;
      const theta = Math.random() * Math.PI * 2;
      const phi = Math.acos(2 * Math.random() - 1);
      positions.set(
        [
          r * Math.sin(phi) * Math.cos(theta),
          r * Math.cos(phi) * 0.6,
          r * Math.sin(phi) * Math.sin(theta),
        ],
        i * 3,
      );
      palette[i % 3]!.toArray(colors, i * 3);
    }
    return { positions, colors };
  }, [count]);
  useFrame((_, dt) => {
    if (ref.current) ref.current.rotation.y -= dt * 0.03;
  });
  return (
    <points ref={ref}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[positions, 3]} />
        <bufferAttribute attach="attributes-color" args={[colors, 3]} />
      </bufferGeometry>
      <pointsMaterial
        size={0.045}
        vertexColors
        transparent
        opacity={0.85}
        sizeAttenuation
        depthWrite={false}
      />
    </points>
  );
}

/** Tilts the whole scene a little towards the pointer. */
function Parallax({ children }: { children: React.ReactNode }) {
  const ref = useRef<THREE.Group>(null);
  useFrame(({ pointer }) => {
    if (!ref.current) return;
    ref.current.rotation.x = THREE.MathUtils.lerp(ref.current.rotation.x, -pointer.y * 0.25, 0.05);
    ref.current.rotation.y = THREE.MathUtils.lerp(ref.current.rotation.y, pointer.x * 0.35, 0.05);
  });
  return <group ref={ref}>{children}</group>;
}

export default function HeroScene({ compact = false }: { compact?: boolean }) {
  const still = prefersReducedMotion();
  return (
    <Canvas
      camera={{ position: [0, 1.2, compact ? 10 : 8.5], fov: 45 }}
      dpr={[1, 1.75]}
      frameloop={still ? "demand" : "always"}
      gl={{ antialias: true, alpha: true }}
      aria-hidden
    >
      <ambientLight intensity={0.7} />
      <directionalLight position={[5, 6, 4]} intensity={1.4} />
      <pointLight position={[-4, -2, 3]} intensity={30} color={ACCENT} />
      <Parallax>
        <Core />
        <Orbit />
        <Particles count={compact ? 500 : 900} />
      </Parallax>
    </Canvas>
  );
}

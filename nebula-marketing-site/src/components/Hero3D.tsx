import { Canvas, useFrame } from '@react-three/fiber'
import { Sphere, MeshDistortMaterial } from '@react-three/drei'
import { useRef, Suspense } from 'react'

function AnimatedSphere() {
    const sphereRef = useRef<any>(null)

    useFrame(({ clock }) => {
        if (sphereRef.current) {
            sphereRef.current.rotation.x = clock.getElapsedTime() * 0.1
            sphereRef.current.rotation.y = clock.getElapsedTime() * 0.15
        }
    })

    return (
        <Sphere ref={sphereRef} args={[1, 32, 64]} scale={2.4}>
            <MeshDistortMaterial
                color="#8B5CF6"
                attach="material"
                distort={0.4}
                speed={1.5}
                roughness={0.2}
                metalness={0.5}
                transparent
                opacity={0.3}
            />
        </Sphere>
    )
}

function Scene() {
    return (
        <>
            <ambientLight intensity={0.5} />
            <directionalLight position={[10, 10, 5]} intensity={1} color="#9F7AEA" />
            <pointLight position={[-10, -10, -10]} intensity={0.5} color="#3B82F6" />
            <AnimatedSphere />
        </>
    )
}

export default function Hero3D() {
    return (
        <div className="absolute inset-0 z-0 pointer-events-none opacity-60">
            <Canvas camera={{ position: [0, 0, 5], fov: 45 }}>
                <Suspense fallback={null}>
                    <Scene />
                </Suspense>
            </Canvas>
        </div>
    )
}

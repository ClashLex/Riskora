import Dither from './components/Dither'
import App from './App'

export default function Stage() {
  return (
    <div className="app-stage">
      <div className="dither-backdrop" aria-hidden="true">
        <Dither
          waveColor="#474747"
          backgroundColor="#ffffff"
          palette={['#ffffff', '#f3f3f3', '#d6d6d6', '#888888']}
          pixelSize={6}
          scale={1.15}
          contrast={0.9}
          brightness={-0.14}
          mouseEffect="ripple"
          mouseRadius={0.2}
          mouseStrength={0.7}
          trail={0.45}
          dpr={1}
        />
      </div>
      <App />
    </div>
  )
}

import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Vite proxy: forward /api to the FastAPI backend (uvicorn api:app --port 8000)
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
})

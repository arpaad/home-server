import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router'

import App from './App'
import './index.css'
import { MemberProvider } from './member/MemberProvider'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // The list is shared between two people, so a stale view is worth
      // refreshing whenever the app is looked at again.
      refetchOnWindowFocus: true,
      staleTime: 10_000,
      retry: 1,
    },
  },
})

const root = document.getElementById('root')
if (!root) throw new Error('missing #root')

createRoot(root).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <MemberProvider>
          <App />
        </MemberProvider>
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
)

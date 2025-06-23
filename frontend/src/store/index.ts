import { configureStore } from '@reduxjs/toolkit'
import authReducer from './authSlice'
import serversReducer from './serversSlice'
import jobsReducer from './jobsSlice'

export const store = configureStore({
  reducer: {
    auth: authReducer,
    servers: serversReducer,
    jobs: jobsReducer,
  },
})

export type RootState = ReturnType<typeof store.getState>
export type AppDispatch = typeof store.dispatch
import { useEffect } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { RootState, AppDispatch } from '../store'
import { setAuth, clearAuth, setLoading } from '../store/authSlice'
import { authAPI } from '../services/api'

export const useAuth = () => {
  const dispatch = useDispatch<AppDispatch>()
  const { user, token, isAuthenticated, loading } = useSelector(
    (state: RootState) => state.auth
  )

  useEffect(() => {
    const checkAuth = async () => {
      const storedToken = localStorage.getItem('token')
      if (!storedToken) {
        dispatch(setLoading(false))
        return
      }

      try {
        const response = await authAPI.getMe()
        console.log('Auth check response:', response.data)
        if (response.data) {
          dispatch(setAuth({ user: response.data, token: storedToken }))
        } else {
          console.log('No user data in response')
          dispatch(clearAuth())
        }
      } catch (error) {
        console.error('Auth check failed:', error)
        dispatch(clearAuth())
      } finally {
        dispatch(setLoading(false))
      }
    }

    checkAuth()
  }, [dispatch])

  const login = async () => {
    try {
      const response = await authAPI.login()
      window.location.href = response.data.url
    } catch (error) {
      console.error('Login failed:', error)
    }
  }

  const logout = async () => {
    try {
      await authAPI.logout()
      dispatch(clearAuth())
    } catch (error) {
      console.error('Logout failed:', error)
      dispatch(clearAuth())
    }
  }

  return {
    user,
    token,
    isAuthenticated,
    loading,
    login,
    logout,
  }
}
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
        if (response.data) {
          dispatch(setAuth({ user: response.data, token: storedToken }))
        } else {
          dispatch(clearAuth())
        }
      } catch (error) {
        dispatch(clearAuth())
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
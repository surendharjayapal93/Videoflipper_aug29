import { useContext } from 'react';
import { AuthContext, type AuthContextValue } from '@/context/AuthContext';

/** Access the current auth state and actions. Must be used within an AuthProvider. */
export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

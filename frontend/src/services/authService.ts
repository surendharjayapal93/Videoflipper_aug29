import { api } from '@/services/api';
import type {
  AuthTokens,
  LoginCredentials,
  RegisterCredentials,
  UpdateProfileData,
  User,
} from '@/types';

/** Raw shapes returned by the backend (snake_case) before mapping to app types. */
interface AuthTokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

interface UserResponse {
  id: number;
  email: string;
  full_name: string | null;
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
}

function mapTokens(data: AuthTokenResponse): AuthTokens {
  return {
    accessToken: data.access_token,
    refreshToken: data.refresh_token,
    tokenType: data.token_type,
  };
}

function mapUser(data: UserResponse): User {
  return {
    id: data.id,
    email: data.email,
    fullName: data.full_name,
    isActive: data.is_active,
    isVerified: data.is_verified,
    createdAt: data.created_at,
  };
}

export async function register(credentials: RegisterCredentials): Promise<AuthTokens> {
  const { data } = await api.post<AuthTokenResponse>('/auth/register', {
    email: credentials.email,
    password: credentials.password,
    full_name: credentials.fullName,
  });
  return mapTokens(data);
}

export async function login(credentials: LoginCredentials): Promise<AuthTokens> {
  const { data } = await api.post<AuthTokenResponse>('/auth/login', {
    email: credentials.email,
    password: credentials.password,
  });
  return mapTokens(data);
}

export async function refreshTokens(refreshToken: string): Promise<AuthTokens> {
  const { data } = await api.post<AuthTokenResponse>('/auth/refresh', {
    refresh_token: refreshToken,
  });
  return mapTokens(data);
}

export async function logout(refreshToken: string): Promise<void> {
  await api.post('/auth/logout', { refresh_token: refreshToken });
}

export async function getCurrentUser(): Promise<User> {
  const { data } = await api.get<UserResponse>('/auth/me');
  return mapUser(data);
}

export async function updateProfile(update: UpdateProfileData): Promise<User> {
  const { data } = await api.put<UserResponse>('/auth/me', {
    full_name: update.fullName,
  });
  return mapUser(data);
}

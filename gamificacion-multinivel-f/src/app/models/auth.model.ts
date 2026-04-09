export type AuthApiRole = 'admin' | 'cliente' | 'employee';

export interface LoginResponseUser {
  userId?: string | number;
  name: string;
  role: AuthApiRole;
  canAccessAdmin?: boolean;
  privileges?: Record<string, boolean>;
  isSuperUser?: boolean;
  discountPercent?: number;
  discountActive?: boolean;
  level?: string;
}

export interface LoginResponse {
  /** JWT de sesión que se persiste en localStorage para Authorization Bearer. */
  token?: string;
  user?: LoginResponseUser;
  id?: string | number;
  name?: string;
  role?: AuthApiRole;
  message?: string;
  Error?: string;
}

export interface CreateAccountPayload {
  name: string;
  email: string;
  phone?: string;
  password: string;
  confirmPassword: string;
  referralToken?: string;
  productId?: string;
}

export interface CreateAccountCustomer {
  id: number | string;
  name: string;
  email: string;
  leaderId?: number | string | null;
  level?: string;
  isAssociate?: boolean;
  discount?: string;
  activeBuyer?: boolean;
  discountRate?: number;
  commissions?: number;
}

export interface CreateAccountResponse {
  ok?: boolean;
  customerId?: number | string;
  customer?: CreateAccountCustomer;
  requiresEmailVerification?: boolean;
  message?: string;
}

export interface VerifyEmailResponse {
  ok: boolean;
  message?: string;
}

export interface PasswordRecoveryRequestPayload {
  email: string;
}

export interface PasswordRecoveryRequestResponse {
  ok: boolean;
  message: string;
}

export interface ResetPasswordPayload {
  email: string;
  otp: string;
  password: string;
  confirmPassword: string;
}

export interface ResetPasswordResponse {
  ok: boolean;
  message: string;
}

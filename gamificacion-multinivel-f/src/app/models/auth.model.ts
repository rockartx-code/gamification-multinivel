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
  customer: CreateAccountCustomer;
  requiresEmailVerification?: boolean;
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

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
}

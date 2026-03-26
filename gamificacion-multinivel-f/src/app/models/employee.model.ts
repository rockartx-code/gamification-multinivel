import { UserPrivileges } from './privileges.model';

export interface AdminEmployee {
  id: number;
  name: string;
  email: string;
  phone?: string;
  canAccessAdmin: boolean;
  privileges: UserPrivileges;
  active: boolean;
  createdAt?: string;
  tempPassword?: string;
}

export interface CreateEmployeePayload {
  name: string;
  email: string;
  phone?: string;
  canAccessAdmin?: boolean;
  privileges?: UserPrivileges;
}

export interface UpdateEmployeePrivilegesPayload {
  canAccessAdmin?: boolean;
  privileges?: UserPrivileges;
}

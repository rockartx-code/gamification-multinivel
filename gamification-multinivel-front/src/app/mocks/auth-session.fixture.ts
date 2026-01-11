import { UserRole } from '../domain/models';

export interface AuthAccount {
  email: string;
  password: string;
  role: UserRole;
}

export const authAccounts: AuthAccount[] = [
  {
    email: 'admin@demo.com',
    password: 'admin123',
    role: 'admin',
  },
  {
    email: 'user@demo.com',
    password: 'user123',
    role: 'user',
  },
];

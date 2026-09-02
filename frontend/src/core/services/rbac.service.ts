import { Injectable, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';

import { Observable, tap } from 'rxjs';

export type PwmsRole = 'VIEWER' | 'ADMIN' | 'SUPERUSER';

export interface CurrentUserPermissions {
  can_manage_users: boolean;
  can_edit_prices: boolean;
  can_assign_superuser: boolean;
}

export interface CurrentUser {
  id: number;
  first_name: string;
  last_name: string;
  username: string;
  email: string;
  role: PwmsRole;
  status: string;
  is_active: boolean;
  last_login: string | null;
  date_joined: string;
  permissions: CurrentUserPermissions;
}

/**
 * Centralized authentication/role state for RBAC decisions in the
 * UI. This is display/navigation logic ONLY - every action is
 * still independently authorized by the Django backend, which is
 * the single source of truth. Hiding a control here never
 * substitutes for a server-side permission check.
 */
@Injectable({
  providedIn: 'root',
})
export class RbacService {
  private readonly http = inject(HttpClient);

  private readonly baseUrl = 'http://localhost:8000/api/settings';

  private readonly currentUserSignal = signal<CurrentUser | null>(null);

  readonly currentUser = this.currentUserSignal.asReadonly();

  private loaded = false;

  // ======================================================
  // LOAD
  // ======================================================

  load(): Observable<CurrentUser> {
    return this.http.get<CurrentUser>(`${this.baseUrl}/me/`, { withCredentials: true }).pipe(
      tap((user) => {
        this.currentUserSignal.set(user);
        this.loaded = true;
      }),
    );
  }

  clear(): void {
    this.currentUserSignal.set(null);
    this.loaded = false;
  }

  isLoaded(): boolean {
    return this.loaded;
  }

  // ======================================================
  // ROLE CHECKS
  // ======================================================

  role(): PwmsRole | null {
    return this.currentUserSignal()?.role ?? null;
  }

  isViewer(): boolean {
    return this.role() === 'VIEWER';
  }

  isAdmin(): boolean {
    return this.role() === 'ADMIN';
  }

  isSuperUser(): boolean {
    return this.role() === 'SUPERUSER';
  }

  canManageUsers(): boolean {
    return !!this.currentUserSignal()?.permissions?.can_manage_users;
  }

  canEditPrices(): boolean {
    return !!this.currentUserSignal()?.permissions?.can_edit_prices;
  }

  canAssignSuperUser(): boolean {
    return !!this.currentUserSignal()?.permissions?.can_assign_superuser;
  }
}

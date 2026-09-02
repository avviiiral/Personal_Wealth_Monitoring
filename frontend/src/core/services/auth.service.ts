import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';

import { Observable, BehaviorSubject, tap, catchError, of } from 'rxjs';

import { RbacService } from './rbac.service';

export interface AuthUser {
  id: number;
  username: string;
  email: string;
}

export interface LoginResponse {
  authenticated: boolean;
  user: AuthUser;
}

@Injectable({
  providedIn: 'root',
})
export class AuthService {
  private readonly http = inject(HttpClient);

  private readonly rbacService = inject(RbacService);

  private readonly baseUrl = 'http://localhost:8000/api/auth';

  private readonly authenticatedSubject = new BehaviorSubject<boolean>(false);

  readonly authenticated$ = this.authenticatedSubject.asObservable();

  private readonly userSubject = new BehaviorSubject<AuthUser | null>(null);

  readonly user$ = this.userSubject.asObservable();

  private authenticationChecked = false;

  // ----------------------------------------------------------
  // LOGIN
  // ----------------------------------------------------------

  login(username: string, password: string): Observable<LoginResponse> {
    return this.http
      .post<LoginResponse>(
        `${this.baseUrl}/login/`,
        {
          username,
          password,
        },
        {
          withCredentials: true,
        },
      )
      .pipe(
        tap((response) => {
          this.authenticatedSubject.next(response.authenticated);

          this.userSubject.next(response.user);

          this.authenticationChecked = true;
        }),
      );
  }

  // ----------------------------------------------------------
  // CURRENT USER
  // ----------------------------------------------------------

  me(): Observable<LoginResponse> {
    if (this.authenticationChecked) {
      if (this.authenticatedSubject.value) {
        return of({
          authenticated: true,
          user: this.userSubject.value!,
        });
      }

      return of({
        authenticated: false,
        user: null as any,
      });
    }

    return this.http
      .get<LoginResponse>(`${this.baseUrl}/me/`, {
        withCredentials: true,
      })
      .pipe(
        tap((response) => {
          this.authenticatedSubject.next(response.authenticated);

          this.userSubject.next(response.user);

          this.authenticationChecked = true;
        }),

        catchError((error) => {
          this.authenticatedSubject.next(false);
          this.userSubject.next(null);

          this.authenticationChecked = true;

          throw error;
        }),
      );
  }

  // ----------------------------------------------------------
  // LOGOUT
  // ----------------------------------------------------------

  logout(): Observable<any> {
    return this.http
      .post(
        `${this.baseUrl}/logout/`,
        {},
        {
          withCredentials: true,
        },
      )
      .pipe(
        tap(() => {
          this.authenticatedSubject.next(false);
          this.userSubject.next(null);

          this.authenticationChecked = true;

          this.rbacService.clear();
        }),
      );
  }

  // ----------------------------------------------------------
  // STATE
  // ----------------------------------------------------------

  isAuthenticated(): boolean {
    return this.authenticatedSubject.value;
  }

  get currentUser(): AuthUser | null {
    return this.userSubject.value;
  }
}

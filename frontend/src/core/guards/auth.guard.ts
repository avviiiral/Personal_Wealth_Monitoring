import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { catchError, map, of } from 'rxjs';

import { AuthService } from '../services/auth.service';

export const authGuard: CanActivateFn = () => {
  const authService = inject(AuthService);
  const router = inject(Router);

  if (authService.isAuthenticated()) {
    return true;
  }

  return authService.me().pipe(
    map(() => true),

    catchError((error) => {
      console.log('User is not authenticated. Redirecting to login.', error.status);

      return of(router.createUrlTree(['/login']));
    }),
  );
};

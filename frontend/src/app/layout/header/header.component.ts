import { Component, HostListener, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';

import { AuthService } from '../../../core/services/auth.service';

@Component({
  selector: 'app-header',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './header.component.html',
  styleUrl: './header.component.scss',
})
export class HeaderComponent {
  private readonly authService = inject(AuthService);
  private readonly router = inject(Router);

  profileMenuOpen = false;
  loggingOut = false;

  get currentUser() {
    return this.authService.currentUser;
  }

  toggleProfileMenu(event: MouseEvent): void {
    event.stopPropagation();
    this.profileMenuOpen = !this.profileMenuOpen;
  }

  openSettings(): void {
    this.profileMenuOpen = false;
    this.router.navigate(['/settings']);
  }

  logout(): void {
    if (this.loggingOut) {
      return;
    }

    this.loggingOut = true;
    this.profileMenuOpen = false;

    this.authService.logout().subscribe({
      next: () => {
        this.loggingOut = false;
        this.router.navigate(['/login']);
      },

      error: (error) => {
        console.error('Logout failed:', error);

        /*
         * Clear the local authentication state even if
         * the backend request fails.
         */
        this.loggingOut = false;
        this.router.navigate(['/login']);
      },
    });
  }

  @HostListener('document:click')
  closeProfileMenu(): void {
    this.profileMenuOpen = false;
  }
}

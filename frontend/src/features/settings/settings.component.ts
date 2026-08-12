import { ChangeDetectorRef, Component, OnInit, inject } from '@angular/core';

import { CommonModule } from '@angular/common';

import { FormsModule } from '@angular/forms';

import { Router } from '@angular/router';

import { AuthService } from '../../core/services/auth.service';

import {
  SettingsApiService,
  SettingsProfile,
  SettingsPreferences,
} from '../../core/services/settings-api.service';

@Component({
  selector: 'app-settings',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './settings.component.html',
  styleUrl: './settings.component.scss',
})
export class SettingsComponent implements OnInit {
  private readonly settingsApi = inject(SettingsApiService);

  private readonly authService = inject(AuthService);

  private readonly router = inject(Router);

  private readonly cdr = inject(ChangeDetectorRef);

  profile: SettingsProfile | null = null;

  preferences: SettingsPreferences = {
    currency: 'INR',
    date_format: 'DD MMM YYYY',
    default_analytics_period: 30,
  };

  email = '';

  currentPassword = '';
  newPassword = '';
  confirmPassword = '';

  loading = true;

  saving = false;

  changingPassword = false;

  loggingOut = false;

  error = '';

  profileMessage = '';

  passwordMessage = '';

  passwordError = '';

  ngOnInit(): void {
    this.loadSettings();
  }

  // ======================================================
  // LOAD
  // ======================================================

  loadSettings(): void {
    this.loading = true;

    this.error = '';

    this.settingsApi.getSettings().subscribe({
      next: (response) => {
        this.profile = response.profile;

        this.preferences = {
          ...response.preferences,
        };

        this.email = response.profile.email;

        this.loading = false;

        this.cdr.detectChanges();
      },

      error: (error) => {
        console.error('Settings loading error:', error);

        this.loading = false;

        this.error = error?.error?.detail || 'Unable to load settings.';

        this.cdr.detectChanges();
      },
    });
  }

  // ======================================================
  // SAVE SETTINGS
  // ======================================================

  saveSettings(): void {
    if (this.saving) {
      return;
    }

    this.saving = true;

    this.profileMessage = '';

    this.error = '';

    this.settingsApi
      .updateSettings({
        email: this.email,

        currency: this.preferences.currency,

        date_format: this.preferences.date_format,

        default_analytics_period: this.preferences.default_analytics_period,
      })
      .subscribe({
        next: (response) => {
          this.profile = response.profile;

          this.preferences = {
            ...response.preferences,
          };

          this.email = response.profile.email;

          this.saving = false;

          this.profileMessage = 'Settings saved successfully.';

          this.cdr.detectChanges();
        },

        error: (error) => {
          console.error('Settings save error:', error);

          this.saving = false;

          this.error = error?.error?.detail || 'Unable to save settings.';

          this.cdr.detectChanges();
        },
      });
  }

  // ======================================================
  // CHANGE PASSWORD
  // ======================================================

  changePassword(): void {
    if (this.changingPassword) {
      return;
    }

    this.passwordError = '';

    this.passwordMessage = '';

    if (!this.currentPassword) {
      this.passwordError = 'Enter your current password.';

      return;
    }

    if (!this.newPassword) {
      this.passwordError = 'Enter a new password.';

      return;
    }

    if (this.newPassword !== this.confirmPassword) {
      this.passwordError = 'New passwords do not match.';

      return;
    }

    this.changingPassword = true;

    this.settingsApi
      .changePassword(this.currentPassword, this.newPassword, this.confirmPassword)
      .subscribe({
        next: () => {
          this.changingPassword = false;

          this.currentPassword = '';

          this.newPassword = '';

          this.confirmPassword = '';

          this.passwordMessage = 'Password changed successfully.';

          this.cdr.detectChanges();
        },

        error: (error) => {
          console.error('Password change error:', error);

          this.changingPassword = false;

          const detail = error?.error?.detail;

          if (Array.isArray(detail)) {
            this.passwordError = detail.join(' ');
          } else {
            this.passwordError = detail || 'Unable to change password.';
          }

          this.cdr.detectChanges();
        },
      });
  }

  // ======================================================
  // LOGOUT
  // ======================================================

  logout(): void {
    if (this.loggingOut) {
      return;
    }

    const confirmed = window.confirm('Are you sure you want to log out?');

    if (!confirmed) {
      return;
    }

    this.loggingOut = true;

    this.authService.logout().subscribe({
      next: () => {
        this.loggingOut = false;

        this.router.navigate(['/login']);
      },

      error: (error) => {
        console.error('Logout error:', error);

        this.loggingOut = false;

        this.error = 'Unable to log out.';

        this.cdr.detectChanges();
      },
    });
  }

  refresh(): void {
    this.loadSettings();
  }
}

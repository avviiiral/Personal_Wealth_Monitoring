import { Routes } from '@angular/router';

import { ShellComponent } from './layout/shell/shell.component';

import { DashboardComponent } from '../features/dashboard/dashboard.component';
import { LoginComponent } from '../features/login/login.component';
import { PortfolioComponent } from '../features/portfolio/portfolio.component';
import { HoldingsComponent } from '../features/holdings/holdings.component';
import { MutualFundsComponent } from '../features/mutual-funds/mutual-funds.component';
import { SipsComponent } from '../features/sips/sips.component';
import { AnalyticsComponent } from '../features/analytics/analytics.component';
import { SettingsComponent } from '../features/settings/settings.component';

import { PagePlaceholderComponent } from '../shared/components/page-placeholder.component';

import { authGuard } from '../core/guards/auth.guard';

export const routes: Routes = [
  // ----------------------------------------------------------
  // Public routes
  // ----------------------------------------------------------

  {
    path: 'login',
    component: LoginComponent,
  },

  // ----------------------------------------------------------
  // Protected PWMS application
  // ----------------------------------------------------------

  {
    path: '',
    component: ShellComponent,

    canActivate: [authGuard],

    children: [
      {
        path: '',
        redirectTo: 'dashboard',
        pathMatch: 'full',
      },

      {
        path: 'dashboard',
        component: DashboardComponent,
      },

      {
        path: 'portfolio',
        component: PortfolioComponent,
      },

      {
        path: 'holdings',
        component: HoldingsComponent,
      },

      {
        path: 'mutual-funds',
        component: MutualFundsComponent,
      },

      {
        path: 'sips',
        component: SipsComponent,
      },

      {
        path: 'analytics',
        component: AnalyticsComponent,
      },

      {
        path: 'settings',
        component: SettingsComponent,
      },
    ],
  },

  // ----------------------------------------------------------
  // Unknown route
  // ----------------------------------------------------------

  {
    path: '**',
    redirectTo: 'dashboard',
  },
];

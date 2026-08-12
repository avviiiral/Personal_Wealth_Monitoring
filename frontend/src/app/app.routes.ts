import { Routes } from '@angular/router';

import { ShellComponent } from './layout/shell/shell.component';

import { DashboardComponent } from '../features/dashboard/dashboard.component';
import { LoginComponent } from '../features/login/login.component';
import { PortfolioComponent } from '../features/portfolio/portfolio.component';
import { HoldingsComponent } from '../features/holdings/holdings.component';

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
        component: PagePlaceholderComponent,
        data: {
          title: 'Mutual Funds',
          description: 'Monitor your mutual fund investments and NAV history.',
        },
      },

      {
        path: 'sips',
        component: PagePlaceholderComponent,
        data: {
          title: 'SIPs',
          description: 'Manage your systematic investment plans.',
        },
      },

      {
        path: 'analytics',
        component: PagePlaceholderComponent,
        data: {
          title: 'Analytics',
          description: 'Analyze your wealth, returns, allocation, and performance.',
        },
      },

      {
        path: 'settings',
        component: PagePlaceholderComponent,
        data: {
          title: 'Settings',
          description: 'Configure your PWMS preferences and account settings.',
        },
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

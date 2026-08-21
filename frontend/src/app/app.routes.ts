import { Routes } from '@angular/router';

import { ShellComponent } from './layout/shell/shell.component';

import { DashboardComponent } from '../features/dashboard/dashboard.component';
import { LoginComponent } from '../features/login/login.component';
import { PortfolioComponent } from '../features/portfolio/portfolio.component';

import { AnalyticsComponent } from '../features/analytics/analytics.component';
import { SettingsComponent } from '../features/settings/settings.component';
import { AiChatComponent } from '../features/ai-chat/ai-chat.component';

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
        path: 'analytics',
        component: AnalyticsComponent,
      },

      {
        path: 'settings',
        component: SettingsComponent,
      },

      {
        path: 'ai-chat',
        component: AiChatComponent,
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

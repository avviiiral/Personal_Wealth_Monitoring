import { Component } from '@angular/core';

import {
  LucideChartPie,
  LucideCircleDollarSign,
  LucideLayoutDashboard,
  LucideSettings,
  LucideTrendingUp,
  LucideWallet,
} from '@lucide/angular';

import { RouterLink, RouterLinkActive } from '@angular/router';

@Component({
  selector: 'app-sidebar',
  standalone: true,
  imports: [
    RouterLink,
    RouterLinkActive,

    LucideLayoutDashboard,
    LucideWallet,
    LucideTrendingUp,
    LucideCircleDollarSign,
    LucideChartPie,
    LucideSettings,
  ],
  templateUrl: './sidebar.component.html',
  styleUrl: './sidebar.component.scss',
})
export class SidebarComponent {}

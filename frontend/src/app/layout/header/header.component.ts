import { Component } from '@angular/core';

import { LucideBell, LucideSearch } from '@lucide/angular';

@Component({
  selector: 'app-header',
  standalone: true,
  imports: [LucideBell, LucideSearch],
  templateUrl: './header.component.html',
  styleUrl: './header.component.scss',
})
export class HeaderComponent {}

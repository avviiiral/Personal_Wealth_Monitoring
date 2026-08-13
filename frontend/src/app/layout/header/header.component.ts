import { Component, HostListener, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';

import { AuthService } from '../../../core/services/auth.service';

interface ChatMessage {
  role: 'user' | 'assistant';
  text: string;
}

@Component({
  selector: 'app-header',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './header.component.html',
  styleUrl: './header.component.scss',
})
export class HeaderComponent {
  private readonly authService = inject(AuthService);
  private readonly router = inject(Router);

  profileMenuOpen = false;
  loggingOut = false;

  /*
   * SEARCH
   */
  searchOpen = false;
  searchText = '';

  /*
   * AI CHAT
   */
  chatOpen = false;
  chatMessage = '';
  chatLoading = false;

  chatMessages: ChatMessage[] = [];

  get currentUser() {
    return this.authService.currentUser;
  }

  /*
   * --------------------------------------------------
   * PROFILE MENU
   * --------------------------------------------------
   */

  toggleProfileMenu(event: MouseEvent): void {
    event.stopPropagation();

    this.profileMenuOpen = !this.profileMenuOpen;

    if (this.profileMenuOpen) {
      this.searchOpen = false;
      this.chatOpen = false;
    }
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

        this.loggingOut = false;
        this.router.navigate(['/login']);
      },
    });
  }

  /*
   * --------------------------------------------------
   * DASHBOARD SEARCH
   * --------------------------------------------------
   */

  toggleSearch(event: MouseEvent): void {
    event.stopPropagation();

    this.searchOpen = !this.searchOpen;

    if (this.searchOpen) {
      this.chatOpen = false;
      this.profileMenuOpen = false;
    }
  }

  closeSearch(): void {
    this.searchOpen = false;
    this.searchText = '';
  }

  /*
   * --------------------------------------------------
   * AI CHAT WINDOW
   * --------------------------------------------------
   */

  toggleChat(event: MouseEvent): void {
    event.stopPropagation();

    this.chatOpen = !this.chatOpen;

    if (this.chatOpen) {
      this.searchOpen = false;
      this.profileMenuOpen = false;
    }
  }

  closeChat(): void {
    this.chatOpen = false;
  }

  /*
   * --------------------------------------------------
   * CHAT MESSAGE
   * --------------------------------------------------
   */

  handleChatKeydown(event: KeyboardEvent): void {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();

      if (!this.chatLoading && this.chatMessage.trim()) {
        this.sendChatMessage();
      }
    }
  }

  sendChatMessage(): void {
    const message = this.chatMessage.trim();

    if (!message || this.chatLoading) {
      return;
    }

    this.chatMessages.push({
      role: 'user',
      text: message,
    });

    this.chatMessage = '';
    this.chatLoading = true;

    /*
     * AI API will be connected here later.
     *
     * For now we only provide a temporary response so
     * that the chatbot window can be tested without
     * an API key.
     */

    setTimeout(() => {
      this.chatMessages.push({
        role: 'assistant',
        text: 'AI chatbot is ready. The AI API connection will be added next.',
      });

      this.chatLoading = false;
    }, 500);
  }

  /*
   * --------------------------------------------------
   * CLOSE MENUS WHEN CLICKING OUTSIDE
   * --------------------------------------------------
   */

  @HostListener('document:click')
  closeMenus(): void {
    this.profileMenuOpen = false;
    this.searchOpen = false;
  }
}

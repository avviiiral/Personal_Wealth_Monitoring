import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface AiChatResponse {
  answer?: string;
  error?: string;
  detail?: any;
}

@Injectable({
  providedIn: 'root',
})
export class AiChatApiService {
  private readonly http = inject(HttpClient);

  private readonly baseUrl = 'http://localhost:8000/api/ai';

  sendMessage(message: string): Observable<AiChatResponse> {
    return this.http.post<AiChatResponse>(
      `${this.baseUrl}/chat/`,
      {
        message,
      },
      {
        withCredentials: true,
      },
    );
  }
}

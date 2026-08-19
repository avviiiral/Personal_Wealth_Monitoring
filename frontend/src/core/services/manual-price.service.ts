import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';

import { Observable } from 'rxjs';

export interface ManualPriceResponse {
  success: boolean;
  message: string;

  data?: {
    asset_id: number;
    asset_name: string;
    price: string;
    price_date: string;
    current_price: string;
    current_value: string;
    unrealized_pnl: string;
  };
}

@Injectable({
  providedIn: 'root',
})
export class ManualPriceService {
  private readonly http = inject(HttpClient);

  private readonly baseUrl = 'http://localhost:8000/api/portfolio';

  private readCsrfToken(): string {
    const cookies = document.cookie.split(';');

    for (const cookie of cookies) {
      const trimmed = cookie.trim();

      if (trimmed.startsWith('csrftoken=')) {
        return decodeURIComponent(trimmed.substring('csrftoken='.length));
      }
    }

    return '';
  }

  private getHeaders(): HttpHeaders {
    const csrfToken = this.readCsrfToken();

    let headers = new HttpHeaders();

    if (csrfToken) {
      headers = headers.set('X-CSRFToken', csrfToken);
    }

    return headers;
  }

  updatePrice(assetId: number, price: number, priceDate?: string): Observable<ManualPriceResponse> {
    return this.http.put<ManualPriceResponse>(
      `${this.baseUrl}/assets/${assetId}/manual-price/`,
      {
        price,
        ...(priceDate
          ? {
              price_date: priceDate,
            }
          : {}),
      },
      {
        headers: this.getHeaders(),
        withCredentials: true,
      },
    );
  }

  deletePrice(assetId: number): Observable<ManualPriceResponse> {
    return this.http.delete<ManualPriceResponse>(
      `${this.baseUrl}/assets/${assetId}/manual-price/`,
      {
        headers: this.getHeaders(),
        withCredentials: true,
      },
    );
  }
}

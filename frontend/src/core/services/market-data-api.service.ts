import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface StockSearchResult {
  symbol: string;
  name: string;
  short_name: string;
  exchange: string;
  quote_type: string;
  isin: string | null;
  currency: string;
}

export interface StockSearchResponse {
  count: number;
  results: StockSearchResult[];
}

@Injectable({
  providedIn: 'root',
})
export class MarketDataApiService {
  private readonly http = inject(HttpClient);

  private readonly baseUrl = 'http://localhost:8000/api/market-data';

  private readonly requestOptions = {
    withCredentials: true,
  };

  searchStocks(search: string, type: 'STOCK' | 'ETF' = 'STOCK'): Observable<StockSearchResponse> {
    let params = new HttpParams().set('search', search.trim()).set('type', type);

    return this.http.get<StockSearchResponse>(`${this.baseUrl}/stocks/search/`, {
      ...this.requestOptions,
      params,
    });
  }
}

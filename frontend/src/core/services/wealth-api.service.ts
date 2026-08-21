import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';

import { Observable } from 'rxjs';

@Injectable({
  providedIn: 'root',
})
export class WealthApiService {
  private readonly http = inject(HttpClient);

  /*
   * IMPORTANT:
   *
   * Frontend:
   *     http://localhost:4200
   *
   * Backend:
   *     http://localhost:8000
   *
   * Use localhost for both so the Django session cookie
   * belongs to the same site.
   */
  private readonly baseUrl = 'http://localhost:8000/api/analytics/wealth';

  getSummary(): Observable<any> {
    return this.http.get<any>(`${this.baseUrl}/summary/`, {
      withCredentials: true,
    });
  }

  getAllocation(): Observable<any> {
    return this.http.get<any>(`${this.baseUrl}/allocation/`, {
      withCredentials: true,
    });
  }

  getPerformance(): Observable<any> {
    return this.http.get<any>(`${this.baseUrl}/performance/`, {
      withCredentials: true,
    });
  }

  getXirr(): Observable<any> {
    return this.http.get<any>(`${this.baseUrl}/xirr/`, {
      withCredentials: true,
    });
  }

  getInvestmentSummary(): Observable<any> {
    return this.http.get<any>(`${this.baseUrl}/investment-summary/`, {
      withCredentials: true,
    });
  }

  getHistorical(days: number = 30): Observable<any> {
    const params = new HttpParams().set('days', days);

    return this.http.get<any>(`${this.baseUrl}/historical/`, {
      params,
      withCredentials: true,
    });
  }
}

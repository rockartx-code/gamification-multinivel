import { Injectable } from '@angular/core';
import { Observable, of } from 'rxjs';
import { delay } from 'rxjs/operators';

@Injectable({ providedIn: 'root' })
export class ApiClient {
  get<T>(payload: T, delayMs = 300): Observable<T> {
    return of(payload).pipe(delay(delayMs));
  }
}

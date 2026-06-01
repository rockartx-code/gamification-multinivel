import { Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';

import { PrivacyNoticeComponent } from './components/privacy-notice/privacy-notice.component';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet, PrivacyNoticeComponent],
  templateUrl: './app.html',
  styleUrl: './app.css'
})
export class App {}

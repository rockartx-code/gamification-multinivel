import { Component } from '@angular/core';

@Component({
  selector: 'app-landing',
  standalone: true,
  templateUrl: './landing.component.html',
  styleUrl: './landing.component.css'
})
export class LandingComponent {
  readonly currentYear = new Date().getFullYear();
}

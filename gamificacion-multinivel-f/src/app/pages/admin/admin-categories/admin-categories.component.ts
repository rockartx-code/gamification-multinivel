import { CommonModule } from '@angular/common';
import { Component, Input, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { finalize } from 'rxjs';

import { UiButtonComponent } from '../../../components/ui-button/ui-button.component';
import { ProductCategory } from '../../../models/admin.model';
import { ApiService } from '../../../services/api.service';

interface CategoryNode extends ProductCategory {
  children: CategoryNode[];
  depth: number;
}

@Component({
  selector: 'app-admin-categories',
  standalone: true,
  imports: [CommonModule, FormsModule, UiButtonComponent],
  templateUrl: './admin-categories.component.html'
})
export class AdminCategoriesComponent implements OnInit {
  @Input() initialCategories: ProductCategory[] = [];

  categories: ProductCategory[] = [];
  isLoading = false;
  isSaving = false;
  isDeleting = false;
  message = '';
  messageTone: 'success' | 'error' = 'success';

  editingId: string | null = null;
  addingParentId: string | null | undefined = undefined; // undefined = closed, null = root
  draftName = '';

  constructor(private readonly api: ApiService) {}

  ngOnInit(): void {
    this.categories = [...this.initialCategories];
  }

  get tree(): CategoryNode[] {
    return this.buildTree(null, 0);
  }

  private buildTree(parentId: string | null, depth: number): CategoryNode[] {
    return this.categories
      .filter((c) => (c.parentId ?? null) === parentId && c.active !== false)
      .sort((a, b) => (a.position ?? 0) - (b.position ?? 0))
      .map((c) => ({ ...c, children: this.buildTree(c.id, depth + 1), depth }));
  }

  startAdd(parentId: string | null): void {
    this.addingParentId = parentId;
    this.editingId = null;
    this.draftName = '';
  }

  startEdit(cat: ProductCategory): void {
    this.editingId = cat.id;
    this.addingParentId = undefined;
    this.draftName = cat.name;
  }

  cancelEdit(): void {
    this.editingId = null;
    this.addingParentId = undefined;
    this.draftName = '';
  }

  save(): void {
    const name = this.draftName.trim();
    if (!name || this.isSaving) return;

    const payload = this.editingId
      ? { id: this.editingId, name, parentId: this.categories.find((c) => c.id === this.editingId)?.parentId, active: true }
      : { name, parentId: this.addingParentId ?? null, active: true, position: this.categories.filter((c) => (c.parentId ?? null) === (this.addingParentId ?? null)).length };

    this.isSaving = true;
    this.api.saveCategory(payload)
      .pipe(finalize(() => { this.isSaving = false; }))
      .subscribe({
        next: (cat) => {
          const idx = this.categories.findIndex((c) => c.id === cat.id);
          if (idx >= 0) { this.categories = this.categories.map((c) => c.id === cat.id ? cat : c); }
          else { this.categories = [...this.categories, cat]; }
          this.cancelEdit();
          this.showMessage(`Categoría guardada: ${cat.name}`, 'success');
        },
        error: () => this.showMessage('No se pudo guardar.', 'error')
      });
  }

  delete(id: string): void {
    const hasChildren = this.categories.some((c) => c.parentId === id);
    if (hasChildren) { this.showMessage('Elimina las subcategorías primero.', 'error'); return; }
    if (this.isDeleting) return;
    this.isDeleting = true;
    this.api.deleteCategory(id)
      .pipe(finalize(() => { this.isDeleting = false; }))
      .subscribe({
        next: () => {
          this.categories = this.categories.filter((c) => c.id !== id);
          this.showMessage('Categoría eliminada.', 'success');
        },
        error: () => this.showMessage('No se pudo eliminar.', 'error')
      });
  }

  private showMessage(msg: string, tone: 'success' | 'error'): void {
    this.message = msg;
    this.messageTone = tone;
    window.setTimeout(() => { this.message = ''; }, 3000);
  }
}

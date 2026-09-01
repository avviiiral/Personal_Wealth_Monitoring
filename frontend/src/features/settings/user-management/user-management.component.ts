import { ChangeDetectorRef, Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

import { RbacService } from '../../../core/services/rbac.service';
import { ToastService } from '../../../core/services/toast.service';

import {
  CreateUserPayload,
  FamilyGroup,
  ManagedUser,
  UpdateUserPayload,
  UserManagementApiService,
} from '../../../core/services/user-management-api.service';

import { PwmsRole } from '../../../core/services/rbac.service';

type ModalMode = 'add' | 'edit' | null;

@Component({
  selector: 'app-user-management',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './user-management.component.html',
  styleUrl: './user-management.component.scss',
})
export class UserManagementComponent implements OnInit {
  private readonly api = inject(UserManagementApiService);

  private readonly rbac = inject(RbacService);

  private readonly toast = inject(ToastService);

  private readonly cdr = inject(ChangeDetectorRef);

  users: ManagedUser[] = [];

  loading = true;

  error = '';

  groups: FamilyGroup[] = [];

  // --------------------------------------------------------
  // MODAL STATE
  // --------------------------------------------------------

  modalMode: ModalMode = null;

  saving = false;

  formErrors: Record<string, string> = {};

  editingUserId: number | null = null;

  form: {
    first_name: string;
    last_name: string;
    username: string;
    email: string;
    role: PwmsRole;
    is_active: boolean;
    password: string;
    confirm_password: string;
    family_group_id: number | null;
  } = this.emptyForm();

  // --------------------------------------------------------
  // DELETE STATE
  // --------------------------------------------------------

  deletingUser: ManagedUser | null = null;

  deleteConfirmText = '';

  deleting = false;

  // --------------------------------------------------------
  // RESET PASSWORD STATE
  // --------------------------------------------------------

  resetPasswordUserId: number | null = null;

  resetPasswordValue = '';

  resetPasswordConfirm = '';

  resettingPassword = false;

  ngOnInit(): void {
    this.loadUsers();
    this.loadGroups();
  }

  // ==========================================================
  // PERMISSIONS (display only - backend is authoritative)
  // ==========================================================

  canAssignSuperUser(): boolean {
    return this.rbac.canAssignSuperUser();
  }

  currentUserId(): number | null {
    return this.rbac.currentUser()?.id ?? null;
  }

  assignableRoles(): PwmsRole[] {
    return this.canAssignSuperUser() ? ['VIEWER', 'ADMIN', 'SUPERUSER'] : ['VIEWER', 'ADMIN'];
  }

  // ==========================================================
  // LOAD
  // ==========================================================

  loadUsers(): void {
    this.loading = true;

    this.error = '';

    this.api.listUsers().subscribe({
      next: (users) => {
        this.users = users;

        this.loading = false;

        this.cdr.detectChanges();
      },

      error: (err) => {
        this.loading = false;

        this.error = this.extractError(err) || 'Unable to load users.';

        this.cdr.detectChanges();
      },
    });
  }

  loadGroups(): void {
    this.api.listGroups().subscribe({
      next: (groups) => {
        this.groups = groups;

        this.cdr.detectChanges();
      },

      error: () => {
        // Non-fatal: the Add/Edit User group dropdown simply shows
        // no options if this fails; the user list itself still works.
      },
    });
  }

  // ==========================================================
  // ADD USER
  // ==========================================================

  openAddUser(): void {
    this.modalMode = 'add';
    this.editingUserId = null;
    this.formErrors = {};
    this.form = this.emptyForm();
  }

  openEditUser(user: ManagedUser): void {
    this.modalMode = 'edit';
    this.editingUserId = user.id;
    this.formErrors = {};
    this.form = {
      first_name: user.first_name || '',
      last_name: user.last_name || '',
      username: user.username,
      email: user.email,
      role: user.role,
      is_active: user.is_active,
      password: '',
      confirm_password: '',
      family_group_id: user.family_group?.id ?? null,
    };
  }

  closeModal(): void {
    this.modalMode = null;
    this.editingUserId = null;
    this.formErrors = {};
    this.saving = false;
  }

  submitForm(): void {
    if (this.saving) {
      return;
    }

    this.formErrors = {};

    if (this.modalMode === 'add') {
      this.submitAddUser();
    } else if (this.modalMode === 'edit' && this.editingUserId !== null) {
      this.submitEditUser(this.editingUserId);
    }
  }

  private submitAddUser(): void {
    if (!this.form.username.trim()) {
      this.formErrors['username'] = 'Username is required.';
      return;
    }

    if (!this.form.email.trim()) {
      this.formErrors['email'] = 'Email is required.';
      return;
    }

    if (!this.form.password) {
      this.formErrors['password'] = 'Password is required.';
      return;
    }

    if (this.form.password !== this.form.confirm_password) {
      this.formErrors['confirm_password'] = 'Passwords do not match.';
      return;
    }

    const payload: CreateUserPayload = {
      first_name: this.form.first_name,
      last_name: this.form.last_name,
      username: this.form.username.trim(),
      email: this.form.email.trim(),
      password: this.form.password,
      confirm_password: this.form.confirm_password,
      role: this.form.role,
      is_active: this.form.is_active,
      family_group_id: this.form.family_group_id,
    };

    this.saving = true;

    this.api.createUser(payload).subscribe({
      next: (user) => {
        this.saving = false;

        this.toast.success(`User "${user.username}" created successfully.`);

        this.closeModal();
        this.loadUsers();
      },

      error: (err) => {
        this.saving = false;

        this.applyFieldErrors(err);

        this.cdr.detectChanges();
      },
    });
  }

  private submitEditUser(userId: number): void {
    if (!this.form.username.trim()) {
      this.formErrors['username'] = 'Username is required.';
      return;
    }

    if (!this.form.email.trim()) {
      this.formErrors['email'] = 'Email is required.';
      return;
    }

    const payload: UpdateUserPayload = {
      first_name: this.form.first_name,
      last_name: this.form.last_name,
      username: this.form.username.trim(),
      email: this.form.email.trim(),
    };

    // Only send role/is_active if this user is allowed to manage
    // them - avoids the backend rejecting a self-edit for
    // attempting to touch fields a Viewer editing themselves isn't
    // allowed to send. Admin/Super User always sends both.
    if (this.rbac.canManageUsers()) {
      payload.role = this.form.role;
      payload.is_active = this.form.is_active;
      payload.family_group_id = this.form.family_group_id;
    }

    this.saving = true;

    this.api.updateUser(userId, payload).subscribe({
      next: (user) => {
        this.saving = false;

        this.toast.success(`User "${user.username}" updated successfully.`);

        this.closeModal();
        this.loadUsers();
      },

      error: (err) => {
        this.saving = false;

        this.applyFieldErrors(err);

        this.cdr.detectChanges();
      },
    });
  }

  // ==========================================================
  // ACTIVATE / DEACTIVATE
  // ==========================================================

  toggleActive(user: ManagedUser): void {
    const action = user.is_active
      ? this.api.deactivateUser(user.id)
      : this.api.activateUser(user.id);

    action.subscribe({
      next: (updated) => {
        this.toast.success(
          `User "${updated.username}" ${updated.is_active ? 'activated' : 'deactivated'}.`,
        );

        this.loadUsers();
      },

      error: (err) => {
        this.toast.error(this.extractError(err) || 'Unable to update user status.');
      },
    });
  }

  // ==========================================================
  // RESET PASSWORD
  // ==========================================================

  openResetPassword(user: ManagedUser): void {
    this.resetPasswordUserId = user.id;
    this.resetPasswordValue = '';
    this.resetPasswordConfirm = '';
  }

  closeResetPassword(): void {
    this.resetPasswordUserId = null;
    this.resetPasswordValue = '';
    this.resetPasswordConfirm = '';
    this.resettingPassword = false;
  }

  submitResetPassword(): void {
    if (this.resetPasswordUserId === null || this.resettingPassword) {
      return;
    }

    if (!this.resetPasswordValue) {
      this.toast.error('Enter a new password.');
      return;
    }

    if (this.resetPasswordValue !== this.resetPasswordConfirm) {
      this.toast.error('New passwords do not match.');
      return;
    }

    this.resettingPassword = true;

    this.api
      .resetPassword(this.resetPasswordUserId, this.resetPasswordValue, this.resetPasswordConfirm)
      .subscribe({
        next: () => {
          this.resettingPassword = false;

          this.toast.success('Password reset successfully.');

          this.closeResetPassword();
        },

        error: (err) => {
          this.resettingPassword = false;

          this.toast.error(this.extractError(err) || 'Unable to reset password.');

          this.cdr.detectChanges();
        },
      });
  }

  // ==========================================================
  // DELETE
  // ==========================================================

  openDeleteUser(user: ManagedUser): void {
    this.deletingUser = user;
    this.deleteConfirmText = '';
  }

  closeDeleteUser(): void {
    this.deletingUser = null;
    this.deleteConfirmText = '';
    this.deleting = false;
  }

  canConfirmDelete(): boolean {
    return !!this.deletingUser && this.deleteConfirmText === this.deletingUser.username;
  }

  confirmDeleteUser(): void {
    if (!this.deletingUser || this.deleting || !this.canConfirmDelete()) {
      return;
    }

    const user = this.deletingUser;

    this.deleting = true;

    this.api.deleteUser(user.id).subscribe({
      next: () => {
        this.deleting = false;

        this.toast.success(`User "${user.username}" deleted.`);

        this.closeDeleteUser();
        this.loadUsers();
      },

      error: (err) => {
        this.deleting = false;

        this.toast.error(this.extractError(err) || 'Unable to delete user.');

        this.cdr.detectChanges();
      },
    });
  }

  // ==========================================================
  // FAMILY GROUPS PANEL
  // ==========================================================

  showGroupPanel = false;

  newGroupName = '';

  creatingGroup = false;

  renamingGroupId: number | null = null;

  renameGroupText = '';

  addMemberSelection: Record<number, number | null> = {};

  toggleGroupPanel(): void {
    this.showGroupPanel = !this.showGroupPanel;
  }

  usersNotInGroup(group: FamilyGroup): ManagedUser[] {
    const memberIds = new Set(group.members.map((m) => m.id));

    return this.users.filter((u) => !memberIds.has(u.id));
  }

  createGroup(): void {
    const name = this.newGroupName.trim();

    if (!name || this.creatingGroup) {
      return;
    }

    this.creatingGroup = true;

    this.api.createGroup(name).subscribe({
      next: () => {
        this.creatingGroup = false;
        this.newGroupName = '';

        this.toast.success(`Group "${name}" created.`);

        this.loadGroups();
      },

      error: (err) => {
        this.creatingGroup = false;

        this.toast.error(this.extractError(err) || 'Unable to create group.');

        this.cdr.detectChanges();
      },
    });
  }

  startRenameGroup(group: FamilyGroup): void {
    this.renamingGroupId = group.id;
    this.renameGroupText = group.name;
  }

  cancelRenameGroup(): void {
    this.renamingGroupId = null;
    this.renameGroupText = '';
  }

  saveRenameGroup(group: FamilyGroup): void {
    const name = this.renameGroupText.trim();

    if (!name) {
      return;
    }

    this.api.renameGroup(group.id, name).subscribe({
      next: () => {
        this.cancelRenameGroup();
        this.loadGroups();
      },

      error: (err) => {
        this.toast.error(this.extractError(err) || 'Unable to rename group.');
      },
    });
  }

  deleteGroup(group: FamilyGroup): void {
    const confirmed = window.confirm(
      `Delete group "${group.name}"? Members will no longer share data - their own accounts and data are untouched.`,
    );

    if (!confirmed) {
      return;
    }

    this.api.deleteGroup(group.id).subscribe({
      next: () => {
        this.toast.success(`Group "${group.name}" deleted.`);

        this.loadGroups();
        this.loadUsers();
      },

      error: (err) => {
        this.toast.error(this.extractError(err) || 'Unable to delete group.');
      },
    });
  }

  addMember(group: FamilyGroup): void {
    const userId = this.addMemberSelection[group.id];

    if (!userId) {
      return;
    }

    this.api.addGroupMember(group.id, userId).subscribe({
      next: () => {
        this.addMemberSelection[group.id] = null;

        this.loadGroups();
        this.loadUsers();
      },

      error: (err) => {
        this.toast.error(this.extractError(err) || 'Unable to add member.');
      },
    });
  }

  removeMember(group: FamilyGroup, userId: number): void {
    this.api.removeGroupMember(group.id, userId).subscribe({
      next: () => {
        this.loadGroups();
        this.loadUsers();
      },

      error: (err) => {
        this.toast.error(this.extractError(err) || 'Unable to remove member.');
      },
    });
  }

  // ==========================================================
  // HELPERS
  // ==========================================================

  private emptyForm() {
    return {
      first_name: '',
      last_name: '',
      username: '',
      email: '',
      role: 'VIEWER' as PwmsRole,
      is_active: true,
      password: '',
      confirm_password: '',
      family_group_id: null as number | null,
    };
  }

  private applyFieldErrors(err: any): void {
    const detail = err?.error?.detail;

    if (detail && typeof detail === 'object' && !Array.isArray(detail)) {
      const flattened: Record<string, string> = {};

      for (const key of Object.keys(detail)) {
        const value = detail[key];

        flattened[key] = Array.isArray(value) ? value.join(' ') : String(value);
      }

      this.formErrors = flattened;

      return;
    }

    this.toast.error(this.extractError(err) || 'Unable to save user.');
  }

  private extractError(err: any): string {
    const detail = err?.error?.detail;

    if (!detail) {
      return '';
    }

    if (typeof detail === 'string') {
      return detail;
    }

    if (Array.isArray(detail)) {
      return detail.join(' ');
    }

    if (typeof detail === 'object') {
      return Object.values(detail)
        .map((value) => (Array.isArray(value) ? value.join(' ') : String(value)))
        .join(' ');
    }

    return '';
  }

  formatDate(value: string | null): string {
    if (!value) {
      return 'Never';
    }

    const date = new Date(value);

    if (Number.isNaN(date.getTime())) {
      return value;
    }

    return date.toLocaleString('en-IN', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  }
}

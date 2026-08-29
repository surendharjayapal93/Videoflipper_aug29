import { isAxiosError } from 'axios';
import { useState, type FormEvent } from 'react';
import { PageWrapper } from '@/components/layout/PageWrapper';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { useAuth } from '@/hooks/useAuth';
import { updateProfile } from '@/services/authService';
import type { ApiError } from '@/types';

/** Protected page showing the current user's account info and an editable full name. */
export function ProfilePage() {
  const { user, refreshUser, logout } = useAuth();
  const [fullName, setFullName] = useState(user?.fullName ?? '');
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | undefined>(undefined);
  const [successMessage, setSuccessMessage] = useState<string | undefined>(undefined);

  if (!user) {
    return null;
  }

  const handleSubmit = async (event: FormEvent<HTMLFormElement>): Promise<void> => {
    event.preventDefault();
    setError(undefined);
    setSuccessMessage(undefined);

    if (!fullName.trim()) {
      setError('Full name is required.');
      return;
    }

    setIsSaving(true);
    try {
      await updateProfile({ fullName });
      await refreshUser();
      setSuccessMessage('Profile updated.');
    } catch (updateError) {
      const message = isAxiosError<ApiError>(updateError)
        ? (updateError.response?.data?.error?.message ?? 'Unable to update your profile.')
        : 'Unable to update your profile.';
      setError(message);
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <PageWrapper>
      <div className="mx-auto w-full max-w-lg space-y-6">
        <div>
          <h1 className="text-2xl font-bold">Your profile</h1>
          <p className="text-sm text-muted-foreground">Manage your account details.</p>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Account</CardTitle>
            <CardDescription>{user.email}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="flex flex-wrap gap-2">
              <Badge variant={user.isVerified ? 'success' : 'warning'}>
                {user.isVerified ? 'Verified' : 'Not verified'}
              </Badge>
              <Badge variant={user.isActive ? 'secondary' : 'destructive'}>
                {user.isActive ? 'Active' : 'Inactive'}
              </Badge>
            </div>

            <form onSubmit={handleSubmit} noValidate className="space-y-4">
              <Input
                label="Full name"
                value={fullName}
                onChange={(event) => setFullName(event.target.value)}
                error={error}
                disabled={isSaving}
              />
              {successMessage && <p className="text-sm text-success">{successMessage}</p>}
              <Button type="submit" variant="gradient" disabled={isSaving}>
                {isSaving ? 'Saving...' : 'Save changes'}
              </Button>
            </form>

            <Button type="button" variant="outline" onClick={() => void logout()}>
              Sign out
            </Button>
          </CardContent>
        </Card>
      </div>
    </PageWrapper>
  );
}

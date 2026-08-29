import { Link } from 'react-router-dom';
import { PageWrapper } from '@/components/layout/PageWrapper';
import { buttonVariants } from '@/components/ui/Button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/Card';

/**
 * Settings landing page. Account/profile fields are edited on `/profile`
 * (owned by the auth module) — this page only hosts app-level settings and
 * links out for account edits, so the profile form isn't duplicated here.
 */
export function SettingsPage() {
  return (
    <PageWrapper>
      <div className="mx-auto w-full max-w-lg space-y-6">
        <div>
          <h1 className="text-2xl font-bold">Settings</h1>
          <p className="text-sm text-muted-foreground">Manage your account and preferences.</p>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Account settings</CardTitle>
            <CardDescription>
              Update your name, email, or password from your profile page.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Link to="/profile" className={buttonVariants({ variant: 'outline' })}>
              Go to profile
            </Link>
          </CardContent>
        </Card>
      </div>
    </PageWrapper>
  );
}

import { useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';
import { PageWrapper } from '@/components/layout/PageWrapper';
import { Button } from '@/components/ui/Button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

/**
 * UI shell for password recovery. No backend endpoint exists yet — submitting
 * only validates the email and moves to a "check your inbox" confirmation state.
 */
export function ForgotPasswordPage() {
  const [email, setEmail] = useState('');
  const [error, setError] = useState<string | undefined>(undefined);
  const [isSubmitted, setIsSubmitted] = useState(false);

  const handleSubmit = (event: FormEvent<HTMLFormElement>): void => {
    event.preventDefault();
    if (!email.trim() || !EMAIL_PATTERN.test(email)) {
      setError('Enter a valid email address.');
      return;
    }
    setError(undefined);
    setIsSubmitted(true);
  };

  return (
    <PageWrapper>
      <div className="flex min-h-[70vh] items-center justify-center">
        <Card className="w-full max-w-sm">
          <CardHeader>
            <CardTitle>Reset your password</CardTitle>
            <CardDescription>
              {isSubmitted
                ? 'Check your inbox for further instructions.'
                : "Enter your email and we'll send you a reset link."}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {isSubmitted ? (
              <div className="space-y-4">
                <p className="text-sm text-muted-foreground">
                  If an account exists for <span className="font-medium text-foreground">{email}</span>,
                  you&apos;ll receive an email with instructions to reset your password shortly.
                </p>
                <Link
                  to="/login"
                  className="block text-center text-sm text-foreground hover:underline"
                >
                  Back to sign in
                </Link>
              </div>
            ) : (
              <form onSubmit={handleSubmit} noValidate className="space-y-4">
                <Input
                  label="Email"
                  type="email"
                  autoComplete="email"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  error={error}
                />
                <Button type="submit" variant="gradient" className="w-full">
                  Send reset link
                </Button>
                <p className="text-center text-sm text-muted-foreground">
                  Remembered your password?{' '}
                  <Link to="/login" className="text-foreground hover:underline">
                    Sign in
                  </Link>
                </p>
              </form>
            )}
          </CardContent>
        </Card>
      </div>
    </PageWrapper>
  );
}

import { useState, type FormEvent } from 'react'
import { getAuthErrorMessage } from '../auth/errors'
import { useAuth } from '../auth/AuthContext'
import { Icon } from '../components/Icon'
import { BrandLockup, BrandMark } from '../components/Brand'

type Mode = 'login' | 'register'

export function AuthPage() {
  const { signIn, signUp, signInWithGoogle, sendPasswordReset } = useAuth()
  const [mode, setMode] = useState<Mode>('login')
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError(null)
    setSuccess(null)

    if (mode === 'register' && password.length < 8) {
      setError('Use at least 8 characters for your password.')
      return
    }

    setBusy(true)
    try {
      if (mode === 'login') {
        await signIn(email.trim(), password)
      } else {
        await signUp(name, email.trim(), password)
      }
    } catch (nextError) {
      setError(getAuthErrorMessage(nextError))
    } finally {
      setBusy(false)
    }
  }

  async function googleSignIn() {
    setError(null)
    setSuccess(null)
    setBusy(true)
    try {
      await signInWithGoogle()
    } catch (nextError) {
      setError(getAuthErrorMessage(nextError))
    } finally {
      setBusy(false)
    }
  }

  async function resetPassword() {
    setError(null)
    setSuccess(null)
    const normalizedEmail = email.trim()
    if (!normalizedEmail) {
      setError('Enter your email address first, then choose Forgot password.')
      return
    }

    setBusy(true)
    try {
      await sendPasswordReset(normalizedEmail)
      setSuccess('Password reset email sent. Check your inbox.')
    } catch (nextError) {
      setError(getAuthErrorMessage(nextError))
    } finally {
      setBusy(false)
    }
  }

  function switchMode(nextMode: Mode) {
    setMode(nextMode)
    setError(null)
    setSuccess(null)
    setPassword('')
  }

  return (
    <main className="min-h-screen bg-[#F7F7FA] px-4 py-8 sm:px-6 lg:grid lg:grid-cols-[minmax(320px,0.82fr)_minmax(540px,1.18fr)] lg:p-0">
      <section className="hidden min-h-screen bg-[#14151C] p-10 text-white lg:flex lg:flex-col lg:justify-between xl:p-14">
        <div>
          <BrandLockup light subtitle="AI lead discovery & outreach" />

          <div className="relative mt-20 max-w-[500px]">
            <div className="pointer-events-none absolute -left-24 -top-20 h-72 w-72 rounded-full bg-[#7B61FF]/14 blur-3xl" />
            <div className="pointer-events-none absolute -bottom-28 left-44 h-56 w-56 rounded-full bg-[#BCE953]/10 blur-3xl" />
            <div className="relative mb-8 inline-flex rounded-[18px] border border-white/10 bg-white/[0.055] p-3 shadow-2xl shadow-black/20">
              <BrandMark className="h-20 w-20" alt="Lead Gen" />
            </div>
            <div className="text-xs font-bold uppercase tracking-[0.14em] text-[#B39CFF]">Simple lead generation</div>
            <h1 className="mt-4 font-display text-[44px] font-bold leading-[1.08] tracking-[-0.045em]">Find the right businesses. Keep the process simple.</h1>
            <p className="mt-5 max-w-[430px] text-[15px] leading-7 text-white/58">Research, organize, and contact leads from one focused workspace. Advanced systems stay behind the interface until you need them.</p>
          </div>
        </div>

        <div className="grid max-w-[450px] grid-cols-3 gap-3">
          {['Find leads', 'Review leads', 'Reach out'].map((item, index) => (
            <div key={item} className="border-t border-white/12 pt-3">
              <div className="text-xs font-bold text-[#B39CFF]">0{index + 1}</div>
              <div className="mt-1 text-sm font-semibold text-white/78">{item}</div>
            </div>
          ))}
        </div>
      </section>

      <section className="flex min-h-[calc(100vh-4rem)] items-center justify-center lg:min-h-screen">
        <div className="w-full max-w-[460px]">
          <div className="mb-8 lg:hidden"><BrandLockup compact subtitle="AI lead discovery & outreach" /></div>

          <div className="card-surface rounded-[16px] p-5 sm:p-8">
            <div>
              <div className="text-xs font-bold uppercase tracking-[0.12em] text-[#7B61FF]">{mode === 'login' ? 'Welcome back' : 'Create account'}</div>
              <h2 className="mt-2 font-display text-[29px] font-bold tracking-[-0.035em] text-[#14151C]">{mode === 'login' ? 'Sign in to your workspace' : 'Start building your lead list'}</h2>
              <p className="mt-2 text-sm leading-6 text-[#6A6D7A]">{mode === 'login' ? 'Use your email or Google account.' : 'Create one account for your leads, integrations, and outreach.'}</p>
            </div>

            <button
              type="button"
              disabled={busy}
              onClick={googleSignIn}
              className="focus-ring mt-7 flex h-11 w-full items-center justify-center gap-2.5 rounded-[10px] border border-[#DCDDE5] bg-white text-sm font-semibold text-[#2E3039] transition hover:bg-[#FAFAFC] disabled:cursor-not-allowed disabled:opacity-60"
            >
              <span className="grid h-5 w-5 place-items-center rounded-full border border-[#D7D8E0] text-[11px] font-extrabold text-[#4285F4]">G</span>
              Continue with Google
            </button>

            <div className="my-6 flex items-center gap-3">
              <div className="h-px flex-1 bg-[#E9E9EF]" />
              <span className="text-[11px] font-semibold uppercase tracking-[0.1em] text-[#989AA5]">or</span>
              <div className="h-px flex-1 bg-[#E9E9EF]" />
            </div>

            <form onSubmit={submit} className="space-y-4">
              {mode === 'register' && (
                <label className="block">
                  <span className="mb-2 block text-[13px] font-semibold text-[#2E3039]">Name</span>
                  <input
                    value={name}
                    onChange={(event) => setName(event.target.value)}
                    autoComplete="name"
                    className="focus-ring h-11 w-full rounded-[10px] border border-[#DCDDE5] bg-white px-3.5 text-sm"
                    placeholder="Your name"
                  />
                </label>
              )}

              <label className="block">
                <span className="mb-2 block text-[13px] font-semibold text-[#2E3039]">Email</span>
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  autoComplete="email"
                  className="focus-ring h-11 w-full rounded-[10px] border border-[#DCDDE5] bg-white px-3.5 text-sm"
                  placeholder="you@company.com"
                />
              </label>

              <label className="block">
                <span className="mb-2 flex items-center justify-between gap-3 text-[13px] font-semibold text-[#2E3039]">
                  <span>Password</span>
                  {mode === 'login' && (
                    <button type="button" disabled={busy} onClick={() => void resetPassword()} className="focus-ring rounded text-xs font-semibold text-[#6D52EE] hover:text-[#7B61FF] disabled:opacity-50">Forgot password?</button>
                  )}
                </span>
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
                  className="focus-ring h-11 w-full rounded-[10px] border border-[#DCDDE5] bg-white px-3.5 text-sm"
                  placeholder={mode === 'login' ? 'Enter your password' : 'At least 8 characters'}
                />
              </label>

              {error && (
                <div role="alert" className="rounded-[10px] border border-[#F2C8C8] bg-[#FFF6F6] px-3.5 py-3 text-sm leading-5 text-[#9D3232]">
                  {error}
                </div>
              )}

              {success && (
                <div role="status" className="rounded-[10px] border border-[#DDECC2] bg-[#F8FDEB] px-3.5 py-3 text-sm leading-5 text-[#4C651F]">
                  {success}
                </div>
              )}

              <button
                type="submit"
                disabled={busy}
                className="focus-ring flex h-11 w-full items-center justify-center gap-2 rounded-[10px] bg-[#7B61FF] px-5 text-sm font-bold text-white shadow-[0_8px_20px_rgba(123,97,255,0.2)] transition hover:bg-[#6E53F0] disabled:cursor-not-allowed disabled:opacity-65"
              >
                {busy ? 'Please wait…' : mode === 'login' ? 'Sign in' : 'Create account'}
                {!busy && <Icon name="arrow" className="h-4 w-4" />}
              </button>
            </form>

            <div className="mt-6 border-t border-[#ECECF1] pt-5 text-center text-sm text-[#6C6F7B]">
              {mode === 'login' ? 'New here?' : 'Already have an account?'}{' '}
              <button
                type="button"
                onClick={() => switchMode(mode === 'login' ? 'register' : 'login')}
                className="focus-ring rounded-md font-bold text-[#6D52EE] hover:text-[#7B61FF]"
              >
                {mode === 'login' ? 'Create account' : 'Sign in'}
              </button>
            </div>
          </div>

          <p className="mt-5 text-center text-xs leading-5 text-[#8A8D98]">Authentication is handled by Firebase. Provider credentials are never stored in the browser by our backend.</p>
        </div>
      </section>
    </main>
  )
}

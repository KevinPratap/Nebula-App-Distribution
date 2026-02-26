
import { FadeIn } from '../components/Animations'

export default function Privacy() {
    return (
        <div className="pt-32 pb-20 px-6 min-h-screen">
            <FadeIn>
                <div className="max-w-3xl mx-auto glass p-10 rounded-3xl border border-white/10">
                    <h1 className="text-4xl font-bold mb-8 tracking-tight">Privacy Policy</h1>
                    <div className="space-y-8 text-white/60 leading-relaxed">
                        <div className="p-4 rounded-2xl bg-white/5 border border-white/10 text-sm italic">
                            Nebula is built on the philosophy of "Local First". Your session data is yours.
                        </div>

                        <section>
                            <h2 className="text-2xl font-bold text-white mb-4">1. Information We Collect</h2>
                            <p className="mb-4">
                                <strong>Account Information:</strong> When you register, we collect your email address and encrypted password.
                            </p>
                            <p>
                                <strong>Usage Data:</strong> We collect anonymized telemetry about app performance and crash reports to improve stability.
                            </p>
                        </section>

                        <section>
                            <h2 className="text-2xl font-bold text-white mb-4">2. Zero-Knowledge Session Audio</h2>
                            <p>
                                Unlike traditional assistants, Nebula Desktop Optimizer processes your meeting audio locally on your machine. We do not stream your audio to our servers for transcription unless you explicitly enable "Cloud Sync" for session history.
                            </p>
                        </section>

                        <section>
                            <h2 className="text-2xl font-bold text-white mb-4">3. Data Security</h2>
                            <p>
                                We implement industry-standard encryption (AES-256) for all data at rest and TLS for data in transit. Your authentication tokens are stored in secure, HttpOnly cookies.
                            </p>
                        </section>

                        <section>
                            <h2 className="text-2xl font-bold text-white mb-4">4. Your Rights</h2>
                            <ul className="list-disc pl-6 space-y-2">
                                <li>The right to a portable copy of your session data.</li>
                                <li>The right to immediate and permanent account deletion.</li>
                                <li>The right to opt-out of anonymized telemetry.</li>
                            </ul>
                        </section>

                        <section className="pt-8 border-t border-white/5">
                            <p>
                                Questions? Email <a href="mailto:support@nebulainterviewai.com" className="text-nebula-purple hover:underline">support@nebulainterviewai.com</a>
                            </p>
                        </section>
                    </div>
                </div>
            </FadeIn>
        </div>
    )
}


import { FadeIn } from '../components/Animations'

export default function Terms() {
    return (
        <div className="pt-32 pb-20 px-6 min-h-screen">
            <FadeIn>
                <div className="max-w-3xl mx-auto glass p-10 rounded-3xl border border-white/10">
                    <h1 className="text-4xl font-bold mb-8 tracking-tight">Terms of Service</h1>
                    <div className="space-y-8 text-white/60 leading-relaxed">
                        <section>
                            <h2 className="text-2xl font-bold text-white mb-4">1. Usage Agreement</h2>
                            <p>
                                By accessing Nebula, you agree to these terms. Nebula is an AI-powered productivity tool. Users are responsible for ensuring that their use of recording and transcription features complies with local laws regarding consent.
                            </p>
                        </section>

                        <section>
                            <h2 className="text-2xl font-bold text-white mb-4">2. Credit System</h2>
                            <p>
                                Nebula operates on a credit-based system. Credits are valid for 12 months from the date of purchase. Refund requests are handled on a case-by-case basis within 14 days of purchase, provided no credits have been consumed.
                            </p>
                        </section>

                        <section>
                            <h2 className="text-2xl font-bold text-white mb-4">3. Prohibited Use</h2>
                            <p>
                                You may not use Nebula to facilitate illegal activities, reverse engineer the desktop client, or attempt to scrape or DDOS our API infrastructure. Accounts found violating these terms will be terminated without refund.
                            </p>
                        </section>

                        <section>
                            <h2 className="text-2xl font-bold text-white mb-4">4. Limitation of Liability</h2>
                            <p>
                                Nebula provides AI assistance "as-is". While we strive for 99% accuracy, we are not liable for any misinterpretations or errors in transcription that lead to business or personal loss.
                            </p>
                        </section>

                        <section className="pt-8 border-t border-white/5">
                            <p>
                                Updates to these terms will be notified via email to active users.
                            </p>
                        </section>
                    </div>
                </div>
            </FadeIn>
        </div>
    )
}

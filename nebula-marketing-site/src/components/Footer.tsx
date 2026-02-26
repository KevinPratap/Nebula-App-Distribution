import React from 'react';
import { motion } from 'framer-motion';
import { Github, Twitter, Mail, Shield, Download, FileText } from 'lucide-react';
import { Link } from 'react-router-dom';

const Footer = () => {
    const currentYear = new Date().getFullYear();

    return (
        <footer className="relative z-10 border-t border-white/5 bg-slate-950/50 pt-20 pb-10 backdrop-blur-xl">
            <div className="container mx-auto px-6">
                <div className="grid grid-cols-1 gap-12 md:grid-cols-4 lg:grid-cols-5">
                    {/* Brand section */}
                    <div className="md:col-span-2 lg:col-span-2">
                        <Link to="/" className="inline-flex items-center gap-2 group">
                            <img
                                src="/logo.png"
                                alt="Nebula Logo"
                                className="h-10 w-auto object-contain brightness-110 group-hover:scale-105 transition-transform origin-left"
                            />
                        </Link>
                        <p className="mt-6 max-w-xs text-sm leading-relaxed text-slate-400">
                            The elite AI assistant for software engineers and technical leaders.
                            Built for performance, privacy, and technical excellence.
                        </p>
                        <div className="mt-8 flex gap-4">
                            <a href="#" className="flex h-10 w-10 items-center justify-center rounded-full border border-white/10 bg-white/5 text-slate-400 transition-all hover:border-violet-500 hover:bg-violet-500/10 hover:text-white">
                                <Twitter className="h-5 w-5" />
                            </a>
                            <a href="#" className="flex h-10 w-10 items-center justify-center rounded-full border border-white/10 bg-white/5 text-slate-400 transition-all hover:border-violet-500 hover:bg-violet-500/10 hover:text-white">
                                <Github className="h-5 w-5" />
                            </a>
                            <a href="mailto:support@nebulainterviewai.com" className="flex h-10 w-10 items-center justify-center rounded-full border border-white/10 bg-white/5 text-slate-400 transition-all hover:border-violet-500 hover:bg-violet-500/10 hover:text-white">
                                <Mail className="h-5 w-5" />
                            </a>
                        </div>
                    </div>

                    {/* Product links */}
                    <div>
                        <h4 className="text-sm font-bold uppercase tracking-widest text-white">Product</h4>
                        <ul className="mt-6 space-y-4">
                            <li>
                                <Link to="/#features" className="text-sm text-slate-400 transition-colors hover:text-white">Features</Link>
                            </li>
                            <li>
                                <Link to="/#pricing" className="text-sm text-slate-400 transition-colors hover:text-white">Pricing</Link>
                            </li>
                            <li>
                                <Link to="/download" className="inline-flex items-center gap-2 text-sm text-slate-400 transition-colors hover:text-white">
                                    <Download className="h-4 w-4" />
                                    Desktop App
                                </Link>
                            </li>
                        </ul>
                    </div>

                    {/* Support links */}
                    <div>
                        <h4 className="text-sm font-bold uppercase tracking-widest text-white">Support</h4>
                        <ul className="mt-6 space-y-4">
                            <li>
                                <Link to="/#faq" className="text-sm text-slate-400 transition-colors hover:text-white">FAQ</Link>
                            </li>
                            <li>
                                <a href="mailto:support@nebulainterviewai.com" className="text-sm text-slate-400 transition-colors hover:text-white">Contact Us</a>
                            </li>
                            <li>
                                <Link to="/status" className="text-sm text-slate-400 transition-colors hover:text-white">System Status</Link>
                            </li>
                        </ul>
                    </div>

                    {/* Legal links */}
                    <div>
                        <h4 className="text-sm font-bold uppercase tracking-widest text-white">Legal</h4>
                        <ul className="mt-6 space-y-4">
                            <li>
                                <Link to="/privacy" className="inline-flex items-center gap-2 text-sm text-slate-400 transition-colors hover:text-white">
                                    <Shield className="h-4 w-4" />
                                    Privacy Policy
                                </Link>
                            </li>
                            <li>
                                <Link to="/terms" className="inline-flex items-center gap-2 text-sm text-slate-400 transition-colors hover:text-white">
                                    <FileText className="h-4 w-4" />
                                    Terms of Service
                                </Link>
                            </li>
                        </ul>
                    </div>
                </div>

                <div className="mt-20 flex flex-col items-center justify-between gap-6 border-t border-white/5 pt-10 md:flex-row">
                    <p className="text-xs text-slate-500">
                        &copy; {currentYear} Nebula AI. All rights reserved. Built for professional technical interview preparedness.
                    </p>
                    <div className="flex items-center gap-2 text-xs font-mono text-slate-500">
                        <span className="h-2 w-2 animate-pulse rounded-full bg-emerald-500"></span>
                        PROD_VERSION_15_STABLE
                    </div>
                </div>
            </div>
        </footer>
    );
};

export default Footer;

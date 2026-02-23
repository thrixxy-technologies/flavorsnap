import { useState } from "react";
import { useTranslation } from "next-i18next";
import { serverSideTranslations } from "next-i18next/serverSideTranslations";
import type { GetStaticProps } from "next";
import Layout from "@/components/Layout";
import Head from "next/head";

interface FormData {
  name: string;
  email: string;
  subject: string;
  message: string;
}

interface FormErrors {
  name?: string;
  email?: string;
  subject?: string;
  message?: string;
}

export default function Contact() {
  const { t } = useTranslation("common");
  const [formData, setFormData] = useState<FormData>({
    name: '',
    email: '',
    subject: '',
    message: ''
  });
  const [errors, setErrors] = useState<FormErrors>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSubmitted, setIsSubmitted] = useState(false);

  const validateForm = (): boolean => {
    const newErrors: FormErrors = {};

    if (!formData.name.trim()) {
      newErrors.name = 'Name is required';
    }

    if (!formData.email.trim()) {
      newErrors.email = 'Email is required';
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      newErrors.email = 'Please enter a valid email address';
    }

    if (!formData.subject.trim()) {
      newErrors.subject = 'Subject is required';
    }

    if (!formData.message.trim()) {
      newErrors.message = 'Message is required';
    } else if (formData.message.trim().length < 10) {
      newErrors.message = 'Message must be at least 10 characters long';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));

    // Clear error for this field when user starts typing
    if (errors[name as keyof FormErrors]) {
      setErrors(prev => ({ ...prev, [name]: undefined }));
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validateForm()) {
      return;
    }

    setIsSubmitting(true);

    try {
      // Simulate API call - replace with actual endpoint
      await new Promise(resolve => setTimeout(resolve, 2000));

      setIsSubmitted(true);
      setFormData({ name: '', email: '', subject: '', message: '' });
      setErrors({});
    } catch (error) {
      console.error('Contact form error:', error);
      setErrors({ message: 'Failed to send message. Please try again.' });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Layout title="Contact - FlavorSnap" description="Get in touch with FlavorSnap team">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        {/* Hero Section */}
        <section className="text-center mb-12" aria-labelledby="contact-heading">
          <h1 id="contact-heading" className="text-4xl md:text-5xl font-bold text-gray-900 mb-4">
            Get in Touch
          </h1>
          <p className="text-xl text-gray-600 max-w-3xl mx-auto">
            Have questions about FlavorSnap? We'd love to hear from you. Send us a message and we'll get back to you as soon as possible.
          </p>
        </section>

        <div className="grid lg:grid-cols-2 gap-12 mb-16">
          {/* Contact Form */}
          <section aria-labelledby="form-heading">
            <h2 id="form-heading" className="text-2xl font-bold text-gray-900 mb-6">
              Send us a Message
            </h2>

            {isSubmitted ? (
              <div className="bg-green-50 border border-green-200 rounded-lg p-6 text-center">
                <div className="text-green-600 text-5xl mb-4">✓</div>
                <h3 className="text-lg font-semibold text-green-800 mb-2">
                  Message Sent Successfully!
                </h3>
                <p className="text-green-700">
                  Thank you for contacting us. We'll get back to you within 24 hours.
                </p>
                <button
                  onClick={() => setIsSubmitted(false)}
                  className="mt-4 bg-green-600 text-white px-6 py-2 rounded-lg hover:bg-green-700 transition-colors focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2"
                >
                  Send Another Message
                </button>
              </div>
            ) : (
              <form onSubmit={handleSubmit} className="space-y-6" noValidate>
                <div>
                  <label htmlFor="name" className="block text-sm font-medium text-gray-700 mb-2">
                    Name *
                  </label>
                  <input
                    type="text"
                    id="name"
                    name="name"
                    value={formData.name}
                    onChange={handleInputChange}
                    className={`w-full px-4 py-3 border rounded-lg focus:outline-none focus:ring-2 focus:ring-accent focus:border-transparent ${errors.name ? 'border-red-300 focus:ring-red-500' : 'border-gray-300'
                      }`}
                    aria-required="true"
                    aria-invalid={!!errors.name}
                    aria-describedby={errors.name ? 'name-error' : undefined}
                    disabled={isSubmitting}
                  />
                  {errors.name && (
                    <p id="name-error" className="mt-2 text-sm text-red-600" role="alert">
                      {errors.name}
                    </p>
                  )}
                </div>
            <p className="text-xl text-gray-600 max-w-3xl mx-auto">
              Have questions about FlavorSnap? We'd love to hear from you. Send us a message and we'll get back to you as soon as possible.
            </p>
          </section>

          <div className="grid lg:grid-cols-2 gap-12 mb-16">
            {/* Contact Form */}
            <section aria-labelledby="form-heading">
              <h2 id="form-heading" className="text-2xl font-bold text-gray-900 mb-6">
                Send us a Message
              </h2>

              {isSubmitted ? (
                <div className="bg-green-50 border border-green-200 rounded-lg p-6 text-center">
                  <div className="text-green-600 text-5xl mb-4">✓</div>
                  <h3 className="text-lg font-semibold text-green-800 mb-2">
                    Message Sent Successfully!
                  </h3>
                  <p className="text-green-700">
                    Thank you for contacting us. We'll get back to you within 24 hours.
                  </p>
                  <button
                    onClick={() => setIsSubmitted(false)}
                    className="mt-4 bg-green-600 text-white px-6 py-2 rounded-lg hover:bg-green-700 transition-colors focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2"
                  >
                    Send Another Message
                  </button>
                </div>
              ) : (
                <form onSubmit={handleSubmit} className="space-y-6" noValidate>
                  <div>
                    <label htmlFor="name" className="block text-sm font-medium text-gray-700 mb-2">
                      Name *
                    </label>
                    <input
                      type="text"
                      id="name"
                      name="name"
                      value={formData.name}
                      onChange={handleInputChange}
                      className={`w-full px-4 py-3 border rounded-lg focus:outline-none focus:ring-2 focus:ring-accent focus:border-transparent ${errors.name ? 'border-red-300 focus:ring-red-500' : 'border-gray-300'
                        }`}
                      aria-required="true"
                      aria-invalid={!!errors.name}
                      aria-describedby={errors.name ? 'name-error' : undefined}
                      disabled={isSubmitting}
                    />
                    {errors.name && (
                      <p id="name-error" className="mt-2 text-sm text-red-600" role="alert">
                        {errors.name}
                      </p>
                    )}
                  </div>

                  <div>
                    <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-2">
                      Email *
                    </label>
                    <input
                      type="email"
                      id="email"
                      name="email"
                      value={formData.email}
                      onChange={handleInputChange}
                      className={`w-full px-4 py-3 border rounded-lg focus:outline-none focus:ring-2 focus:ring-accent focus:border-transparent ${errors.email ? 'border-red-300 focus:ring-red-500' : 'border-gray-300'
                        }`}
                      aria-required="true"
                      aria-invalid={!!errors.email}
                      aria-describedby={errors.email ? 'email-error' : undefined}
                      disabled={isSubmitting}
                    />
                    {errors.email && (
                      <p id="email-error" className="mt-2 text-sm text-red-600" role="alert">
                        {errors.email}
                      </p>
                    )}
                  </div>

                  <div>
                    <label htmlFor="subject" className="block text-sm font-medium text-gray-700 mb-2">
                      Subject *
                    </label>
                    <input
                      type="text"
                      id="subject"
                      name="subject"
                      value={formData.subject}
                      onChange={handleInputChange}
                      className={`w-full px-4 py-3 border rounded-lg focus:outline-none focus:ring-2 focus:ring-accent focus:border-transparent ${errors.subject ? 'border-red-300 focus:ring-red-500' : 'border-gray-300'
                        }`}
                      aria-required="true"
                      aria-invalid={!!errors.subject}
                      aria-describedby={errors.subject ? 'subject-error' : undefined}
                      disabled={isSubmitting}
                    />
                    {errors.subject && (
                      <p id="subject-error" className="mt-2 text-sm text-red-600" role="alert">
                        {errors.subject}
                      </p>
                    )}
                  </div>

                  <div>
                    <label htmlFor="message" className="block text-sm font-medium text-gray-700 mb-2">
                      Message *
                    </label>
                    <textarea
                      id="message"
                      name="message"
                      value={formData.message}
                      onChange={handleInputChange}
                      rows={6}
                      className={`w-full px-4 py-3 border rounded-lg focus:outline-none focus:ring-2 focus:ring-accent focus:border-transparent resize-none ${errors.message ? 'border-red-300 focus:ring-red-500' : 'border-gray-300'
                        }`}
                      aria-required="true"
                      aria-invalid={!!errors.message}
                      aria-describedby={errors.message ? 'message-error' : undefined}
                      disabled={isSubmitting}
                    />
                    {errors.message && (
                      <p id="message-error" className="mt-2 text-sm text-red-600" role="alert">
                        {errors.message}
                      </p>
                    )}
                  </div>

                  <div className="flex items-center justify-between">
                    <p className="text-sm text-gray-500">* Required fields</p>
                    <button
                      type="submit"
                      disabled={isSubmitting}
                      className="bg-accent text-white px-8 py-3 rounded-lg font-semibold hover:bg-accent/90 transition-colors focus:outline-none focus:ring-4 focus:ring-accent/50 focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 disabled:bg-gray-400 disabled:cursor-not-allowed"
                      aria-describedby={isSubmitting ? 'submit-status' : undefined}
                    >
                      {isSubmitting ? (
                        <span className="flex items-center">
                          <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                          </svg>
                          Sending...
                        </span>
                      ) : (
                        'Send Message'
                      )}
                    </button>
                  </div>
                  <div id="submit-status" className="sr-only" role="status" aria-live="polite">
                    {isSubmitting ? 'Sending message' : ''}
                  </div>
                </form>
              )}
            </section>

            {/* Contact Information */}
            <section aria-labelledby="info-heading">
              <h2 id="info-heading" className="text-2xl font-bold text-gray-900 mb-6">
                Other Ways to Reach Us
              </h2>

              <div className="space-y-6">
                <div className="bg-white rounded-xl shadow-md p-6">
                  <div className="flex items-start space-x-4">
                    <div className="text-accent text-2xl">📧</div>
                    <div>
                      <h3 className="font-semibold text-gray-900 mb-1">Email</h3>
                      <p className="text-gray-600">support@flavorsnap.com</p>
                      <p className="text-sm text-gray-500 mt-1">We respond within 24 hours</p>
                    </div>
                  </div>
                </div>

                <div className="bg-white rounded-xl shadow-md p-6">
                  <div className="flex items-start space-x-4">
                    <div className="text-accent text-2xl">💬</div>
                    <div>
                      <h3 className="font-semibold text-gray-900 mb-1">Live Chat</h3>
                      <p className="text-gray-600">Available Monday-Friday, 9AM-6PM EST</p>
                      <button className="mt-2 text-accent hover:text-accent/80 font-medium focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-2 rounded">
                        Start Chat
                      </button>
                    </div>
                  </div>
                </div>

                <div className="bg-white rounded-xl shadow-md p-6">
                  <div className="flex items-start space-x-4">
                    <div className="text-accent text-2xl">🐦</div>
                    <div>
                      <h3 className="font-semibold text-gray-900 mb-1">Social Media</h3>
                      <div className="space-y-2">
                        <a
                          href="#"
                          className="block text-accent hover:text-accent/80 focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-2 rounded"
                        >
                          Twitter: @flavorsnap
                        </a>
                        <a
                          href="#"
                          className="block text-accent hover:text-accent/80 focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-2 rounded"
                        >
                          Instagram: @flavorsnap
                        </a>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="bg-white rounded-xl shadow-md p-6">
                  <div className="flex items-start space-x-4">
                    <div className="text-accent text-2xl">❓</div>
                    <div>
                      <h3 className="font-semibold text-gray-900 mb-1">FAQ</h3>
                      <p className="text-gray-600 mb-2">Find quick answers to common questions</p>
                      <Link
                        href="/faq"
                        className="text-accent hover:text-accent/80 font-medium focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-2 rounded"
                      >
                        View FAQ
                      </Link>
                    </div>
                  </div>
                </div>
              </div>
            </section>
          </div>

          {/* Response Time Info */}
            <section className="bg-gradient-to-r from-accent/10 to-orange-50 rounded-2xl p-8 text-center" aria-labelledby="response-heading">
              <h2 id="response-heading" className="text-2xl font-bold text-gray-900 mb-4">
                Response Times
              </h2>
              <div className="grid md:grid-cols-3 gap-6">
                <div>
                  <div className="text-3xl mb-2">📧</div>
                  <h3 className="font-semibold text-gray-900 mb-1">Email</h3>
                  <p className="text-gray-600">Within 24 hours</p>
                </div>
                <div>
                  <div className="text-3xl mb-2">💬</div>
                  <h3 className="font-semibold text-gray-900 mb-1">Live Chat</h3>
                  <p className="text-gray-600">Instant during business hours</p>
                </div>
                <div>
                  <div className="text-3xl mb-2">🐦</div>
                  <h3 className="font-semibold text-gray-900 mb-1">Social Media</h3>
                  <p className="text-gray-600">Within a few hours</p>
                </div>
              </div>
            </section>
          </main>
        </div>
    </Layout>
  );
}

export const getStaticProps: GetStaticProps = async ({ locale }) => ({
  props: {
    ...(await serverSideTranslations(locale ?? "en", ["common"])),
  },
});

import { themes as prismThemes } from 'prism-react-renderer';

/** @type {import('@docusaurus/types').Config} */
const config = {
  title: 'Geo Murray',
  tagline: ' ',
  favicon: 'img/logo.ico',

  url: 'https://entropyx.github.io',
  baseUrl: '/murray/',

  organizationName: 'entropyx',
  projectName: 'murray',
  deploymentBranch: 'gh-pages',
  trailingSlash: false,
  onBrokenLinks: 'throw',
  onBrokenMarkdownLinks: 'warn',

  i18n: {
    defaultLocale: 'en',
    locales: ['en'],
  },

  presets: [
    [
      'classic',
      {
        docs: {
          sidebarPath: './sidebars.js',
          remarkPlugins: [require('remark-math')],
          rehypePlugins: [require('rehype-katex')],
        },
        blog: {
          showReadingTime: true,
          feedOptions: {
            type: ['rss', 'atom'],
            xslt: true,
          },
          onInlineTags: 'warn',
          onInlineAuthors: 'warn',
          onUntruncatedBlogPosts: 'warn',
          remarkPlugins: [require('remark-math')],
          rehypePlugins: [require('rehype-katex')],
        },
        theme: {
          customCss: './src/css/custom.css',
        },
      },
    ],
  ],

  themeConfig: {
    image: 'img/card_social.jpg',
    navbar: {
      title: 'Murray',
      logo: {
        alt: 'My Site Logo',
        src: 'img/logo.svg',
      },
      items: [
        {
          type: 'docSidebar',
          sidebarId: 'tutorialSidebar',
          position: 'left',
          label: 'Documentation',
        },
        {
          href: 'https://github.com/entropyx/murray',
          label: 'GitHub',
          position: 'right',
        },
      ],
    },
    footer: {
      style: 'dark',
      links: [
        {
          title: 'Learn Murray',
          items: [
            {
              label: 'Documentation',
              to: '/docs/Welcome to Murray',
            },
          ],
        },
        {
          title: 'Community Entropy',
          items: [
            {
              label: 'Official Page',
              href: 'https://entropy.tech/',
            },
            {
              label: 'Facebook',
              href: 'https://www.facebook.com/entropyhq/',
            },
            {
              label: 'LinkedIn',
              href: 'https://www.linkedin.com/company/entropyhq/',
            },
            {
              label: 'Instagram',
              href: 'https://www.instagram.com/entropy.tech/',
            },
          ],
        },
        {
          title: 'More',
          items: [
            {
              label: 'GitHub',
              href: 'https://github.com/entropyx/murray',
            },
          ],
        },
      ],
      copyright: `Copyright © ${new Date().getFullYear()} Murray, Inc. Built with Docusaurus.`,
    },
    prism: {
      theme: prismThemes.vsDark,
      darkTheme: prismThemes.dracula,
    },
  },

  stylesheets: [
    {
      href: 'https://cdn.jsdelivr.net/npm/katex@0.13.18/dist/katex.min.css',
      type: 'text/css',
      integrity:
        'sha384-RsEuMpa6YlMeYf/AYYaOj9xV1ibHj5t/Uybp5G5mY4p3Wtw4l3k47CVlfrF4ruKg',
      crossorigin: 'anonymous',
    },
  ],
};

export default config;

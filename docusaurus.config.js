import { themes as prismThemes } from 'prism-react-renderer';

/** @type {import('@docusaurus/types').Config} */
const config = {
  title: 'Geo Murray',
  tagline: 'Herramienta avanzada para diseño de experimentos geoespaciales',
  favicon: 'img/logo.ico',

  url: 'https://docs-murray.entropy.tech/',
  baseUrl: '/',

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

  // Metadatos personalizados
  customFields: {
    keywords: 'geospatial, experiments, Murray, entropy, analysis',
    description: 'Murray es una herramienta avanzada para el diseño y análisis de experimentos geoespaciales',
  },

  presets: [
    [
      'classic',
      {
        docs: {
          sidebarPath: './sidebars.js',
          remarkPlugins: [require('remark-math')],
          rehypePlugins: [require('rehype-katex')],
          // Configuración adicional para docs
          editUrl: 'https://github.com/entropyx/murray/tree/main/',
          showLastUpdateAuthor: false,
          showLastUpdateTime: true,
          breadcrumbs: true,
        },
        blog: false,
        theme: {
          customCss: './src/css/custom.css',
        },
      },
    ],
  ],

  plugins: [
    // Plugins adicionales (sitemap ya incluido en preset classic)
  ],

  themeConfig: {
    // Metadatos para SEO
    metadata: [
      {name: 'keywords', content: 'geospatial, experiments, Murray, entropy, analysis'},
      {name: 'description', content: 'Murray es una herramienta avanzada para el diseño y análisis de experimentos geoespaciales'},
      {property: 'og:image', content: 'img/card_social.jpg'},
      {property: 'og:type', content: 'website'},
      {name: 'twitter:card', content: 'summary_large_image'},
    ],

    // Configuración de colores del tema
    colorMode: {
      defaultMode: 'light',
      disableSwitch: false,
      respectPrefersColorScheme: true,
    },
    
    // Configuración de anuncios
    announcementBar: {
      id: 'new_version',
      content: '🚀 Descubre las últimas innovaciones en análisis geoespacial con Murray. <a target="_blank" href="https://github.com/entropyx/murray/releases">Explorar funcionalidades</a>',
      backgroundColor: '#3E7CB1',
      textColor: '#ffffff',
      isCloseable: true,
    },

    image: 'img/card_social.jpg',
    navbar: {
      title: 'Murray',
      logo: {
        alt: 'Murray Logo',
        src: 'img/logo.svg',
        srcDark: 'img/logo.svg',
        href: '/',
        target: '_self',
      },
      hideOnScroll: false,
      items: [
        {
          type: 'docSidebar',
          sidebarId: 'tutorialSidebar',
          position: 'left',
          label: 'Documentación',
        },
        {
          href: 'https://github.com/entropyx/murray',
          position: 'right',
          className: 'header-github-link',
          'aria-label': 'GitHub repository',
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
              to: '/docs/Welcome%20to%20Murray',
            },
            {
              label: 'User Guide',
              to: '/docs/tutorial-extras/User%20Guide',
            },
            {
              label: 'Methodology',
              to: '/docs/Methodology',
            },
          ],
        },
        {
          title: 'Resources',
          items: [
            {
              label: 'Examples',
              to: '/docs/Murray%20Python%20Package/Walkthrough',
            },
            {
              label: 'GitHub',
              href: 'https://github.com/entropyx/murray',
            },
            {
              label: 'Issues',
              href: 'https://github.com/entropyx/murray/issues',
            },
          ],
        },
        {
          title: 'Entropy Community',
          items: [
            {
              label: 'Official Site',
              href: 'https://entropyx.github.io',
            },
            {
              label: 'Facebook',
              href: 'https://www.facebook.com/entropyhq/',
            },
            {
              label: 'LinkedIn',
              href: 'https://www.linkedin.com/company/entropyhq/',
            },
          ],
        },
        {
          title: 'Legal',
          items: [
            {
              label: 'License',
              href: 'https://github.com/entropyx/murray/blob/main/LICENSE',
            },
            {
              label: 'Terms of Use',
              href: '#',
            },
          ],
        },
      ],
      logo: {
        alt: 'Murray Logo',
        src: 'img/logo.svg',
        href: 'https://entropyx.github.io',
        width: 160,
        height: 51,
      },
      copyright: `Copyright © ${new Date().getFullYear()} Entropy Labs. Construido con Docusaurus.`,
    },
    prism: {
      theme: prismThemes.github,
      darkTheme: prismThemes.dracula,
      additionalLanguages: ['bash', 'json', 'python', 'javascript', 'typescript'],
    },

    // Configuración de tabla de contenidos
    tableOfContents: {
      minHeadingLevel: 2,
      maxHeadingLevel: 5,
    },
  },

  stylesheets: [
    {
      href: 'https://cdn.jsdelivr.net/npm/katex@0.13.18/dist/katex.min.css',
      type: 'text/css',
      integrity:
        'sha384-RsEuMpa6YlMeYf/AYYaOj9xV1ibHj5t/Uybp3Wtw4l3k47CVlfrF4ruKg',
      crossorigin: 'anonymous',
    },
    // Fuentes adicionales
    {
      href: 'https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap',
      type: 'text/css',
    },
  ],

  scripts: [
    // Analytics (opcional)
    {
      src: 'https://www.googletagmanager.com/gtag/js?id=GA_MEASUREMENT_ID',
      async: true,
    },
  ],
};

export default config;

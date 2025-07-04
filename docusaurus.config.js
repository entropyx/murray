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
    defaultLocale: 'es',
    locales: ['es', 'en'],
  },

  // Metadatos adicionales para SEO
  metadata: [
    {name: 'keywords', content: 'geospatial, experiments, Murray, entropy, analysis'},
    {name: 'description', content: 'Murray es una herramienta avanzada para el diseño y análisis de experimentos geoespaciales'},
    {property: 'og:image', content: 'img/card_social.jpg'},
    {property: 'og:type', content: 'website'},
    {name: 'twitter:card', content: 'summary_large_image'},
  ],
 
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
          showLastUpdateAuthor: true,
          showLastUpdateTime: true,
          breadcrumbs: true,
        },
        blog: {
          showReadingTime: true,
          readingTime: ({content, frontMatter, defaultReadingTime}) =>
            defaultReadingTime({content, options: {wordsPerMinute: 300}}),
          feedOptions: {
            type: ['rss', 'atom'],
            xslt: true,
            title: 'Murray Blog',
            description: 'Noticias y actualizaciones sobre Murray',
          },
          onInlineTags: 'warn',
          onInlineAuthors: 'warn',
          onUntruncatedBlogPosts: 'warn',
          remarkPlugins: [require('remark-math')],
          rehypePlugins: [require('rehype-katex')],
          blogTitle: 'Murray Blog',
          blogDescription: 'Noticias y actualizaciones sobre Murray',
          postsPerPage: 10,
          blogSidebarTitle: 'Artículos recientes',
          blogSidebarCount: 'ALL',
        },
        theme: {
          customCss: './src/css/custom.css',
        },
      },
    ],
  ],

  plugins: [
    // Plugin para sitemap
    [
      '@docusaurus/plugin-sitemap',
      {
        changefreq: 'weekly',
        priority: 0.5,
        ignorePatterns: ['/tags/**'],
        filename: 'sitemap.xml',
      },
    ],
  ],

  themeConfig: {
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
          to: '/blog',
          label: 'Blog',
          position: 'left'
        },
        {
          type: 'search',
          position: 'right',
        },
        {
          type: 'localeDropdown',
          position: 'right',
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
          title: 'Aprende Murray',
          items: [
            {
              label: 'Documentación',
              to: '/docs/Welcome%20to%20Murray',
            },
            {
              label: 'Guía de Usuario',
              to: '/docs/tutorial-extras/User%20Guide',
            },
            {
              label: 'Metodología',
              to: '/docs/Methodology',
            },
          ],
        },
        {
          title: 'Recursos',
          items: [
            {
              label: 'Ejemplos',
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
              label: 'Sitio Oficial',
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
              label: 'Licencia',
              href: 'https://github.com/entropyx/murray/blob/main/LICENSE',
            },
            {
              label: 'Términos de Uso',
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
    // Configuración del algoritmo de búsqueda
    algolia: {
      // Si tienes configurado Algolia
      appId: 'YOUR_APP_ID',
      apiKey: 'YOUR_SEARCH_API_KEY',
      indexName: 'YOUR_INDEX_NAME',
      contextualSearch: true,
      searchParameters: {},
      searchPagePath: 'search',
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
    {
      src: '/js/analytics.js',
      async: true,
    },
  ],
};

export default config;

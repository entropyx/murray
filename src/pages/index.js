import React from 'react';
import clsx from 'clsx';
import Link from '@docusaurus/Link';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
import Layout from '@theme/Layout';
import Heading from '@theme/Heading';
import styles from './index.module.css';

function HomepageHeader() {
  const {siteConfig} = useDocusaurusContext();
  return (
    <header className={clsx('hero hero--primary', styles.heroBanner)}>
      <div className="container">
        <div className={styles.heroInner}>
          <Heading as="h1" className={styles.heroTitle}>
            Are you ready to optimize your geospatial analysis?
          </Heading>
          <p className={styles.heroSubtitle}>
            Advanced geospatial measurement solutions to optimize business growth
          </p>
          <div className={styles.heroButtons}>
            <Link
              className={clsx('button button--primary button--lg', styles.primaryButton)}
              to="/docs/Welcome%20to%20Murray">
              Implement Murray
            </Link>
            <Link
              className={clsx('button button--secondary button--lg', styles.secondaryButton)}
              href="https://github.com/entropyx/murray">
              See on GitHub
            </Link>
          </div>
        </div>
      </div>
    </header>
  );
}

function Feature({title, description, icon, link}) {
  return (
    <div className={styles.feature}>
      <div className={styles.featureIcon}>{icon}</div>
      <h3 className={styles.featureTitle}>{title}</h3>
      <p className={styles.featureDescription}>{description}</p>
      {link && (
        <Link className={styles.featureLink} to={link}>
          Explore more →
        </Link>
      )}
    </div>
  );
}

function StatsSection() {
  return (
    <section className={styles.stats}>
      <div className="container">
        <div className={styles.statsGrid}>
          <div className={styles.statItem}>
            <div className={styles.statNumber}>MMM</div>
            <div className={styles.statLabel}>Incremental measurement for calibration</div>
          </div>
        </div>
      </div>
    </section>
  );
}



export default function Home() {
  const {siteConfig} = useDocusaurusContext();
  return (
    <Layout
      title={`${siteConfig.title} - Advanced Geospatial Analysis`}
      description="Murray provides advanced geospatial measurement solutions to optimize business growth. Powerful, scalable, and reliable.">
      <HomepageHeader />
      <main>
        <section className={styles.features}>
          <div className="container">
            <div className={styles.featuresInner}>
              <Feature
                icon="📊"
                title="Accurate Measurement"
                description="Use advanced mathematical models and statistical models to measure incremental impact."
                link="/docs/Methodology"
              />
              <Feature
                icon="🔬"
                title="Robust Experimentation"
                description="Conduct controlled experiments and geo-lift studies to calibrate and validate your measurement models."
                link="/docs/Murray%20Python%20Package/Walkthrough"
              />
              <Feature
                icon="🔍"
                title="Full visibility"
                description="See the impact of differents scenarios in your business."
                link="/docs/Murray%20Python%20Package/Getting%20Started"
              />
            </div>
          </div>
        </section>
        
        <StatsSection />
        
        <section className={styles.showcase}>
          <div className="container">
            <div className={styles.showcaseContent}>
              <div className={styles.showcaseText}>
                <h2>Powered by Entropy</h2>
                <p>
                  Murray is developed by Entropy, pioneers in marketing science and incremental measurement. 
                  Our experience in Marketing Mix Modeling (MMM) and experimentation guarantees reliable and growth-oriented measurement solutions.
                </p>
                <Link
                  className="button button--primary"
                  href="https://entropy.tech">
                  Learn more about Entropy
                </Link>
              </div>
              <div className={styles.showcaseImage}>
                <img
                  src="/img/heatmap.png"
                  alt="Advanced geospatial analysis with Murray"
                  className={styles.showcaseImg}
                />
              </div>
            </div>
          </div>
        </section>
      </main>
    </Layout>
  );
}

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
    <header className={clsx('hero', styles.heroBanner)}>
      <div className={styles.heroInner}>
        <Heading as="h1" className={styles.heroTitle}>
          Geo Murray
        </Heading>
        <p className={styles.heroSubtitle}>
        Tool for designing geospatial experiments
        </p>
      </div>
      <div className={styles.heroWave}>
        <svg viewBox="0 0 1440 320">
          <path fill="currentColor" d="M0,96L48,112C96,128,192,160,288,160C384,160,480,128,576,112C672,96,768,96,864,112C960,128,1056,160,1152,160C1248,160,1344,128,1392,112L1440,96L1440,320L1392,320C1344,320,1248,320,1152,320C1056,320,960,320,864,320C768,320,672,320,576,320C480,320,384,320,288,320C192,320,96,320,48,320L0,320Z"></path>
        </svg>
      </div>
    </header>
  );
}

function Feature({title, description, icon}) {
  return (
    <div className={styles.feature}>
      <div className={styles.featureIcon}>{icon}</div>
      <h3 className={styles.featureTitle}>{title}</h3>
      <p className={styles.featureDescription}>{description}</p>
    </div>
  );
}

export default function Home() {
  const {siteConfig} = useDocusaurusContext();
  return (
    <Layout
      title={siteConfig.title}
      description="A tool for geographic incrementality testing">
      <HomepageHeader />
      <main>
        <div className={styles.features}>
          <div className={styles.featuresInner}>
            <Feature
              icon="🚀"
              title="Easy to Use"
              description="Murray was designed to be intuitive and accessible to any user."
            />
            <Feature
              icon="📊"
              title="Reliable Results"
              description="Robust methods that generate accurate and reliable results."
            />
            <Feature
              icon="⚡"
              title="High Performance"
              description="Optimized for handling large geospatial datasets."
            />
          </div>
        </div>
      </main>
    </Layout>
  );
}

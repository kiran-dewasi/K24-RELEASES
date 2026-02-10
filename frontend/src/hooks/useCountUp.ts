import { useEffect, useRef } from 'react';

export function useCountUp(end: number, duration: number = 2000) {
    const nodeRef = useRef<HTMLElement | null>(null);

    useEffect(() => {
        const node = nodeRef.current;
        if (!node) return;

        const startTime = performance.now();
        const startValue = 0;

        const animate = (currentTime: number) => {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1);

            // Easing function (easeOutQuart)
            const easeOutQuart = 1 - Math.pow(1 - progress, 4);
            const current = Math.floor(startValue + (end - startValue) * easeOutQuart);

            if (node) {
                node.textContent = current.toLocaleString('en-IN');
            }

            if (progress < 1) {
                requestAnimationFrame(animate);
            } else {
                if (node) {
                    node.textContent = end.toLocaleString('en-IN');
                }
            }
        };

        requestAnimationFrame(animate);
    }, [end, duration]);

    return nodeRef;
}
